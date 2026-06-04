"""Delta sync orchestrator: build bundles, apply them via LWW, manage sync state."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from mnemo_mcp.sync.bundle import decode_bundle, encode_bundle

if TYPE_CHECKING:
    from mnemo_mcp.db import MemoryDB
    from mnemo_mcp.sync import SyncBackend


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def _query_rows_since(db: MemoryDB, since: float | None) -> list[dict]:
    """Query memories updated since ``since`` (UNIX timestamp)."""
    if since is None:
        # Full pull.
        rows = db._conn.execute("SELECT * FROM memories").fetchall()
    else:
        # Delta push.
        since_iso = datetime.fromtimestamp(since, tz=UTC).isoformat()
        rows = db._conn.execute(
            "SELECT * FROM memories WHERE updated_at > ?", (since_iso,)
        ).fetchall()
    return [dict(r) for r in rows]


def _query_kg_since(db: MemoryDB, since: float | None) -> dict[str, list[dict]]:
    """Query KG sections (entities, edges, links) since ``since``."""
    if since is None:
        # Full pull.
        ents = db._conn.execute("SELECT * FROM memory_entities").fetchall()
        edges = db._conn.execute("SELECT * FROM memory_edges").fetchall()
        links = db._conn.execute("SELECT * FROM memory_entity_links").fetchall()
    else:
        since_iso = datetime.fromtimestamp(since, tz=UTC).isoformat()
        ents = db._conn.execute(
            "SELECT * FROM memory_entities WHERE updated_at > ?", (since_iso,)
        ).fetchall()
        # Edges don't have updated_at, use created_at.
        edges = db._conn.execute(
            "SELECT * FROM memory_edges WHERE created_at > ?", (since_iso,)
        ).fetchall()
        # Links don't have timestamps. For delta, we might skip them or send all.
        # Phase 3 sends all links for simplicity as they are small JOIN rows.
        links = db._conn.execute("SELECT * FROM memory_entity_links").fetchall()

    return {
        "entities": [dict(e) for e in ents],
        "edges": [dict(e) for e in edges],
        "links": [dict(link) for link in links],
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _build_payload(
    rows: list[dict],
    since: float | None,
    entities: list[dict] | None = None,
    edges: list[dict] | None = None,
    links: list[dict] | None = None,
) -> dict[str, bytes]:
    """Construct the bundle payload (manifest + memories.jsonl + KG)."""
    manifest = {
        "row_count": len(rows),
        "since": since,
        "schema_version": "mem_003_temporal",
        "entity_count": len(entities or []),
        "edge_count": len(edges or []),
        "link_count": len(links or []),
    }

    payload = {
        "manifest.json": json.dumps(manifest).encode("utf-8"),
        "memories.jsonl": "\n".join(json.dumps(r) for r in rows).encode("utf-8"),
    }

    # Phase 3 KG sections.
    payload["memories_entities.jsonl"] = (
        "\n".join(json.dumps(e) for e in (entities or [])).encode("utf-8")
        if entities
        else b""
    )
    payload["memories_edges.jsonl"] = (
        "\n".join(json.dumps(e) for e in (edges or [])).encode("utf-8")
        if edges
        else b""
    )
    payload["memories_entity_links.jsonl"] = (
        "\n".join(json.dumps(link) for link in (links or [])).encode("utf-8")
        if links
        else b""
    )

    return payload


async def build_delta_bundle(
    db: MemoryDB, since: float | None, passphrase: str
) -> bytes:
    """Query local changes since ``since`` and return an encrypted bundle."""
    rows = await asyncio.to_thread(_query_rows_since, db, since)
    kg = await asyncio.to_thread(_query_kg_since, db, since)
    payload = _build_payload(
        rows,
        since,
        entities=kg["entities"],
        edges=kg["edges"],
        links=kg["links"],
    )
    return encode_bundle(payload, passphrase)


async def build_full_bundle(db: MemoryDB, passphrase: str) -> bytes:
    """Query ALL memories and KG rows and return an encrypted bundle."""
    return await build_delta_bundle(db, since=None, passphrase=passphrase)


# ---------------------------------------------------------------------------
# Apply (LWW per row)
# ---------------------------------------------------------------------------


_INSERT_COLS = (
    "id",
    "content",
    "category",
    "tags",
    "source",
    "created_at",
    "updated_at",
    "access_count",
    "last_accessed",
    "importance",
    "context_type",
    "archived_at",
    "text_raw",
    "compressed",
    "compression_provider",
)


def _ensure_overrides_table(db: MemoryDB) -> None:
    """Create ``sync_overrides`` audit table on first use (idempotent)."""
    db._conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL,
            local_updated_at TEXT,
            remote_updated_at TEXT,
            local_content TEXT,
            remote_content TEXT,
            recorded_at REAL NOT NULL
        )"""
    )


def _upsert_row_lww(db: MemoryDB, remote: dict) -> str:
    """Insert / update / skip per LWW. Returns 'inserted', 'updated', 'skipped'.

    'inserted' = no local row, INSERT OR REPLACE applied.
    'updated' = remote.updated_at > local.updated_at, REPLACE applied.
    'skipped' = local.updated_at >= remote.updated_at, audit row written.
    """
    cursor = db._conn.cursor()
    existing = cursor.execute(
        "SELECT updated_at, content FROM memories WHERE id = ?",
        (remote["id"],),
    ).fetchone()

    if existing is None:
        outcome = "inserted"
    else:
        local_updated = existing["updated_at"]
        remote_updated = remote.get("updated_at", "")
        if local_updated >= remote_updated:
            _ensure_overrides_table(db)
            cursor.execute(
                "INSERT INTO sync_overrides "
                "(memory_id, local_updated_at, remote_updated_at, "
                "local_content, remote_content, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    remote["id"],
                    local_updated,
                    remote_updated,
                    existing["content"],
                    remote.get("content"),
                    time.time(),
                ),
            )
            db._conn.commit()
            return "skipped"
        outcome = "updated"

    placeholders = ", ".join("?" for _ in _INSERT_COLS)
    cols_csv = ", ".join(_INSERT_COLS)
    cursor.execute(
        f"INSERT OR REPLACE INTO memories ({cols_csv}) VALUES ({placeholders})",
        tuple(remote.get(c) for c in _INSERT_COLS),
    )
    db._conn.commit()
    return outcome


def _apply_kg_sections(db: MemoryDB, payload: dict[str, bytes]) -> dict:
    """Apply Phase 3 KG sections (entities + edges + links) via INSERT OR IGNORE.

    Idempotent: replaying the same bundle is safe because the unique
    indexes on ``memory_entities(name, entity_type)`` and
    ``memory_edges(source_id, target_id, relation_type)`` collapse
    duplicates. Returns counts dict.
    """
    counts = {"entities_applied": 0, "edges_applied": 0, "links_applied": 0}
    cursor = db._conn.cursor()

    # 1. Entities
    ents_raw = payload.get("memories_entities.jsonl", b"").decode("utf-8")
    ent_rows = []
    for line in ents_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ent = json.loads(line)
            ent_rows.append(
                (
                    ent.get("id"),
                    ent.get("name"),
                    ent.get("entity_type"),
                    ent.get("created_at"),
                    ent.get("updated_at"),
                )
            )
        except Exception as e:
            logger.debug(f"apply_bundle: entity skipped ({e})")

    if ent_rows:
        try:
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entities "
                "(id, name, entity_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ent_rows,
            )
            counts["entities_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(
                f"apply_bundle: entities bulk insert failed ({e}), falling back"
            )
            for row in ent_rows:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO memory_entities "
                        "(id, name, entity_type, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        row,
                    )
                    counts["entities_applied"] += cursor.rowcount or 0
                except Exception as inner_e:
                    logger.debug(f"apply_bundle: entity skipped ({inner_e})")

    # 2. Edges
    edges_raw = payload.get("memories_edges.jsonl", b"").decode("utf-8")
    edge_rows = []
    for line in edges_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            edge = json.loads(line)
            edge_rows.append(
                (
                    edge.get("id"),
                    edge.get("source_id"),
                    edge.get("target_id"),
                    edge.get("relation_type"),
                    edge.get("created_at"),
                    edge.get("memory_id"),
                    edge.get("valid_from"),
                    edge.get("valid_to"),
                )
            )
        except Exception as e:
            logger.debug(f"apply_bundle: edge skipped ({e})")

    if edge_rows:
        try:
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_edges "
                "(id, source_id, target_id, relation_type, created_at, "
                " memory_id, valid_from, valid_to) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                edge_rows,
            )
            counts["edges_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: edges bulk insert failed ({e}), falling back")
            for row in edge_rows:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO memory_edges "
                        "(id, source_id, target_id, relation_type, created_at, "
                        " memory_id, valid_from, valid_to) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        row,
                    )
                    counts["edges_applied"] += cursor.rowcount or 0
                except Exception as inner_e:
                    logger.debug(f"apply_bundle: edge skipped ({inner_e})")

    # 3. Links
    links_raw = payload.get("memories_entity_links.jsonl", b"").decode("utf-8")
    link_rows = []
    for line in links_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            link = json.loads(line)
            link_rows.append((link.get("memory_id"), link.get("entity_id")))
        except Exception as e:
            logger.debug(f"apply_bundle: link skipped ({e})")

    if link_rows:
        try:
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entity_links "
                "(memory_id, entity_id) VALUES (?, ?)",
                link_rows,
            )
            counts["links_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: links bulk insert failed ({e}), falling back")
            for row in link_rows:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO memory_entity_links "
                        "(memory_id, entity_id) VALUES (?, ?)",
                        row,
                    )
                    counts["links_applied"] += cursor.rowcount or 0
                except Exception as inner_e:
                    logger.debug(f"apply_bundle: link skipped ({inner_e})")

    db._conn.commit()
    return counts


async def apply_bundle(db: MemoryDB, bundle: bytes, passphrase: str) -> dict:
    """Decrypt ``bundle`` and apply each memory row via LWW per row.

    Phase 3 also applies the ``memories_entities.jsonl`` /
    ``memories_edges.jsonl`` / ``memories_entity_links.jsonl`` sections
    via INSERT OR IGNORE so the receiver KG converges with the sender.

    Returns counts dict::

        {
            "inserted": <int>, "updated": <int>, "skipped": <int>,
            "row_count": <int>, "manifest": <decoded manifest dict>,
            "entities_applied": <int>, "edges_applied": <int>,
            "links_applied": <int>,
        }
    """
    payload = decode_bundle(bundle, passphrase)
    manifest = json.loads(payload.get("manifest.json", b"{}").decode("utf-8"))
    memories_jsonl = payload.get("memories.jsonl", b"").decode("utf-8")

    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    rows: list[dict] = []
    for line in memories_jsonl.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("apply_bundle: skipping malformed JSONL line")
            continue

    for row in rows:
        outcome = await asyncio.to_thread(_upsert_row_lww, db, row)
        counts[outcome] += 1

    # Phase 3 KG sections.
    kg_counts = await asyncio.to_thread(_apply_kg_sections, db, payload)

    return {**counts, **kg_counts, "row_count": len(rows), "manifest": manifest}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def sync_now(db: MemoryDB, backend_name: str, passphrase: str) -> dict:
    """Push delta (or full on sequence gap) via the named backend.

    Workflow:

    1. Read local cursor + last sync timestamp from sync_state.
    2. Query backend's last_remote_sequence.
    3. If remote_seq > local_cursor + 1 (another machine pushed) ->
       full pull + merge + full push at remote_seq + 1.
    4. Else delta push at local_cursor + 1.
    5. Persist new cursor + timestamp to sync_state.

    Returns a result dict with ``mode`` ('delta' | 'full-pull-push'),
    ``cursor``, ``rows`` counts, and (when applicable) the merge counts
    from :func:`apply_bundle`.
    """
    from mnemo_mcp.sync import get as get_backend

    backend: SyncBackend = get_backend(backend_name)

    state = await asyncio.to_thread(db.get_sync_state, backend_name) or {}
    local_cursor = int(state.get("upload_cursor") or 0)
    last_sync_at = float(state.get("last_sync_at") or 0.0)

    remote_seq = await backend.last_remote_sequence()

    if remote_seq > local_cursor + 1:
        # Sequence gap -> another machine pushed. Pull full passport,
        # merge LWW, then push consolidated bundle.
        full_bundle = await backend.pull(sequence=None)
        merge_counts = (
            await apply_bundle(db, full_bundle, passphrase)
            if full_bundle
            else {"inserted": 0, "updated": 0, "skipped": 0, "row_count": 0}
        )
        new_full = await build_full_bundle(db, passphrase)
        new_cursor = remote_seq + 1
        await backend.push(new_full, sequence=new_cursor)
        await asyncio.to_thread(
            db.upsert_sync_state,
            backend_name,
            time.time(),
            None,
            new_cursor,
        )
        return {
            "mode": "full-pull-push",
            "cursor": new_cursor,
            "remote_seq_before": remote_seq,
            "merge": merge_counts,
        }

    # Common case: push delta of local changes since last_sync_at.
    delta = await build_delta_bundle(db, since=last_sync_at, passphrase=passphrase)
    new_cursor = local_cursor + 1
    await backend.push(delta, sequence=new_cursor)
    rows = await asyncio.to_thread(_query_rows_since, db, last_sync_at)
    await asyncio.to_thread(
        db.upsert_sync_state, backend_name, time.time(), None, new_cursor
    )
    return {
        "mode": "delta",
        "cursor": new_cursor,
        "rows": len(rows),
    }
