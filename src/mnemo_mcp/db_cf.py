"""D1 + Vectorize backed MemoryDB for the Cloudflare deployment.

Same public surface as mnemo_mcp.db.MemoryDB but: relational + FTS5 + graph +
bitemporal -> D1 (per-sub scoped); embedding vectors -> Vectorize (per-sub
metadata filter). The Python ranking logic (RRF k=60, recency, frequency,
importance) is ported byte-for-byte from db.py in Task 10; only the storage
transport and the FTS+vector split change. Exposes ``_conn`` (a D1Connection) so
graph.py / temporal/queries.py / sync/delta.py work unchanged.

CRUD is ported from db.py (add L517, get L1195, update L1202, delete L1274,
list_memories L1148); every statement carries ``sub`` so a shared D1 stays
per-user isolated (DECISION D3).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from loguru import logger

from mnemo_mcp._d1_conn import D1Connection

MAX_CONTENT_LENGTH = 5000


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MemoryDBD1:
    def __init__(
        self,
        d1,
        vectorize,
        sub: str = "default",
        embedding_dims: int = 0,
        recency_half_life_days: float = 7.0,
        *,
        embedding_model: str = "",
        reindex_on_model_change: bool = False,
    ) -> None:
        self._d1 = d1
        self._vec = vectorize
        self.sub = sub
        self._embedding_dims = embedding_dims
        self._embedding_model = embedding_model
        self._reindex_on_model_change = reindex_on_model_change
        self._recency_half_life = float(recency_half_life_days)
        self._vec_enabled = embedding_dims > 0
        self._conn = D1Connection(d1, sub=sub)  # for graph.py / temporal / sync
        self._guard_embedding_identity()

    @property
    def vec_enabled(self) -> bool:
        return self._vec_enabled

    def get_store_meta(self, key: str) -> str | None:
        rows = self._d1.execute(
            "SELECT value FROM store_meta WHERE sub = ? AND key = ?", [self.sub, key]
        )
        return rows[0]["value"] if rows else None

    def _set_store_meta(self, key: str, value: str) -> None:
        self._d1.execute(
            "INSERT OR REPLACE INTO store_meta (sub, key, value) VALUES (?, ?, ?)",
            [self.sub, key, value],
        )

    def _stamp_embedding_identity(self) -> None:
        self._set_store_meta("embedding_dims", str(self._embedding_dims))
        if self._embedding_model:
            self._set_store_meta("embedding_model", self._embedding_model)

    def _guard_embedding_identity(self) -> None:
        """Per-sub embedding-identity guard, ported from db.py:227-294.

        Stamps a fresh store with the current ``(embedding_model, embedding_dims)``,
        proceeds on a match, and aborts (EmbeddingModelMismatch) on a dims/model
        change unless ``reindex_on_model_change`` is set -- in which case it
        re-stamps and the embed pass re-upserts this sub's vectors. Per-sub so a
        shared D1 never false-blocks one user on another's identity. Dims are
        always compared (even when a model id is absent) since a dims mismatch is
        the most dangerous corruption; operators MUST set REINDEX_ON_MODEL_CHANGE
        before changing EMBEDDING_DIMS.
        """
        from mnemo_mcp.exceptions import EmbeddingModelMismatch

        if self._embedding_dims <= 0:
            return
        stored_model = self.get_store_meta("embedding_model")
        stored_dims_raw = self.get_store_meta("embedding_dims")
        if stored_dims_raw is None and stored_model is None:
            self._stamp_embedding_identity()
            return
        try:
            stored_dims = int(stored_dims_raw) if stored_dims_raw is not None else 0
        except ValueError:
            stored_dims = 0
        dims_match = stored_dims == self._embedding_dims
        model_match = (
            not stored_model
            or not self._embedding_model
            or stored_model == self._embedding_model
        )
        if dims_match and model_match:
            return
        if self._reindex_on_model_change:
            logger.warning(
                "Embedding identity changed (sub={}); REINDEX set -- Vectorize "
                "vectors for this sub will be rebuilt on the next embed pass.",
                self.sub,
            )
            self._stamp_embedding_identity()
            return
        raise EmbeddingModelMismatch(
            stored_model=stored_model or "",
            stored_dims=stored_dims,
            requested_model=self._embedding_model or "",
            requested_dims=self._embedding_dims,
        )

    def add(
        self,
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
        source: str | None = None,
        embedding: list[float] | None = None,
    ) -> str:
        if len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(
                f"Content length {len(content)} exceeds limit of {MAX_CONTENT_LENGTH}"
            )
        memory_id = uuid.uuid4().hex
        now = _now_iso()
        tags_json = "[]" if not tags else json.dumps(tags)
        self._d1.execute(
            "INSERT INTO memories (id, sub, content, category, tags, source, "
            "created_at, updated_at, access_count, last_accessed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            [memory_id, self.sub, content, category, tags_json, source, now, now, now],
        )
        if embedding and self._vec_enabled:
            self._vec.upsert(
                [
                    {
                        "id": f"{self.sub}:{memory_id}",
                        "values": embedding,
                        "metadata": {
                            "sub": self.sub,
                            "mid": memory_id,
                            "category": category,
                            "archived": 0,
                        },
                    }
                ]
            )
        logger.info(f"[AUDIT] add id={memory_id} sub={self.sub} cat={category}")
        return memory_id

    def get(self, memory_id: str) -> dict | None:
        rows = self._d1.execute(
            "SELECT * FROM memories WHERE sub = ? AND id = ?", [self.sub, memory_id]
        )
        return rows[0] if rows else None

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
        importance: float | None = None,
        embedding: list[float] | None = None,
    ) -> bool:
        if content is not None and len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(
                f"Content length {len(content)} exceeds limit of {MAX_CONTENT_LENGTH}"
            )
        # Port db.py:1226-1257 partial update. D1Backend takes positional params,
        # so the named-param CASE-WHEN becomes COALESCE(?, col): a None param
        # keeps the existing value. NULLing a column is not a supported update
        # (none of these columns are nullable in practice), matching local
        # behaviour where an unprovided field is left unchanged.
        self._d1.execute(
            "UPDATE memories SET "
            "content = COALESCE(?, content), category = COALESCE(?, category), "
            "tags = COALESCE(?, tags), source = COALESCE(?, source), "
            "importance = COALESCE(?, importance), updated_at = ? "
            "WHERE sub = ? AND id = ?",
            [
                content,
                category,
                ("[]" if not tags else json.dumps(tags)) if tags is not None else None,
                source,
                max(0.0, min(1.0, importance)) if importance is not None else None,
                _now_iso(),
                self.sub,
                memory_id,
            ],
        )
        # D1 returns no rows for UPDATE, so rowcount is unavailable; confirm the
        # row exists to distinguish "updated" from "missing id".
        if self.get(memory_id) is None:
            return False
        if embedding and self._vec_enabled:
            self._vec.upsert(
                [
                    {
                        "id": f"{self.sub}:{memory_id}",
                        "values": embedding,
                        "metadata": {"sub": self.sub, "mid": memory_id},
                    }
                ]
            )
        logger.info(f"[AUDIT] update id={memory_id} sub={self.sub}")
        return True

    def delete(self, memory_id: str) -> bool:
        if self.get(memory_id) is None:
            return False
        self._d1.execute(
            "DELETE FROM memories WHERE sub = ? AND id = ?", [self.sub, memory_id]
        )
        # Vectorize delete-by-id is a separate REST op exposed by the Worker
        # /vectorize/deleteByIds handler (Task 14); a stale vector is harmless
        # because search() (Task 10) hydrates rows from D1 and drops vector hits
        # with no matching D1 row.
        logger.info(f"[AUDIT] delete id={memory_id} sub={self.sub}")
        return True

    def list_memories(
        self,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
        *,
        include_archived: bool = False,
    ) -> list[dict]:
        limit = max(1, min(int(limit), 100))
        sql = "SELECT * FROM memories WHERE sub = ?"
        params: list = [self.sub]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if not include_archived:
            sql += " AND archived_at IS NULL"
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        return self._d1.execute(sql, params)

    def close(self) -> None:
        return None
