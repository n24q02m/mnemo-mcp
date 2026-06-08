import sys

with open("src/mnemo_mcp/sync/delta.py", "r") as f:
    content = f.read()

search_text = """def _apply_kg_sections(db: MemoryDB, payload: dict[str, bytes]) -> dict:
    \"\"\"Apply Phase 3 KG sections (entities + edges + links) via INSERT OR IGNORE.

    Idempotent: replaying the same bundle is safe because the unique
    indexes on ``memory_entities(name, entity_type)`` and
    ``memory_edges(source_id, target_id, relation_type)`` collapse
    duplicates. Returns counts dict.
    \"\"\"
    counts = {"entities_applied": 0, "edges_applied": 0, "links_applied": 0}
    cursor = db._conn.cursor()

    ents_raw = payload.get("memories_entities.jsonl", b"").decode("utf-8")
    for line in ents_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ent = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO memory_entities "
                "(id, name, entity_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    ent.get("id"),
                    ent.get("name"),
                    ent.get("entity_type"),
                    ent.get("created_at"),
                    ent.get("updated_at"),
                ),
            )
            counts["entities_applied"] += cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: entity skipped ({e})")

    edges_raw = payload.get("memories_edges.jsonl", b"").decode("utf-8")
    for line in edges_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            edge = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO memory_edges "
                "(id, source_id, target_id, relation_type, created_at, "
                " memory_id, valid_from, valid_to) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    edge.get("id"),
                    edge.get("source_id"),
                    edge.get("target_id"),
                    edge.get("relation_type"),
                    edge.get("created_at"),
                    edge.get("memory_id"),
                    edge.get("valid_from"),
                    edge.get("valid_to"),
                ),
            )
            counts["edges_applied"] += cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: edge skipped ({e})")

    links_raw = payload.get("memories_entity_links.jsonl", b"").decode("utf-8")
    for line in links_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            link = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO memory_entity_links "
                "(memory_id, entity_id) VALUES (?, ?)",
                (link.get("memory_id"), link.get("entity_id")),
            )
            counts["links_applied"] += cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: link skipped ({e})")

    db._conn.commit()
    return counts"""

replacement_text = """def _apply_kg_sections(db: MemoryDB, payload: dict[str, bytes]) -> dict:
    \"\"\"Apply Phase 3 KG sections (entities + edges + links) via INSERT OR IGNORE.

    Idempotent: replaying the same bundle is safe because the unique
    indexes on ``memory_entities(name, entity_type)`` and
    ``memory_edges(source_id, target_id, relation_type)`` collapse
    duplicates. Returns counts dict.
    \"\"\"
    counts = {"entities_applied": 0, "edges_applied": 0, "links_applied": 0}
    cursor = db._conn.cursor()

    # 1. Entities
    ents_to_insert = []
    ents_raw = payload.get("memories_entities.jsonl", b"").decode("utf-8")
    for line in ents_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ent = json.loads(line)
            ents_to_insert.append(
                (
                    ent.get("id"),
                    ent.get("name"),
                    ent.get("entity_type"),
                    ent.get("created_at"),
                    ent.get("updated_at"),
                )
            )
        except (json.JSONDecodeError, AttributeError):
            continue

    if ents_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entities "
                "(id, name, entity_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ents_to_insert,
            )
            counts["entities_applied"] = len(ents_to_insert)
        except Exception as e:
            logger.debug(f"apply_bundle: entities bulk insert failed ({e})")

    # 2. Edges
    edges_to_insert = []
    edges_raw = payload.get("memories_edges.jsonl", b"").decode("utf-8")
    for line in edges_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            edge = json.loads(line)
            edges_to_insert.append(
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
        except (json.JSONDecodeError, AttributeError):
            continue

    if edges_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_edges "
                "(id, source_id, target_id, relation_type, created_at, "
                " memory_id, valid_from, valid_to) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                edges_to_insert,
            )
            counts["edges_applied"] = len(edges_to_insert)
        except Exception as e:
            logger.debug(f"apply_bundle: edges bulk insert failed ({e})")

    # 3. Links
    links_to_insert = []
    links_raw = payload.get("memories_entity_links.jsonl", b"").decode("utf-8")
    for line in links_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            link = json.loads(line)
            links_to_insert.append((link.get("memory_id"), link.get("entity_id")))
        except (json.JSONDecodeError, AttributeError):
            continue

    if links_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entity_links "
                "(memory_id, entity_id) VALUES (?, ?)",
                links_to_insert,
            )
            counts["links_applied"] = len(links_to_insert)
        except Exception as e:
            logger.debug(f"apply_bundle: links bulk insert failed ({e})")

    db._conn.commit()
    return counts"""

if search_text not in content:
    print("Could not find search text in src/mnemo_mcp/sync/delta.py")
    sys.exit(1)

new_content = content.replace(search_text, replacement_text)
with open("src/mnemo_mcp/sync/delta.py", "w") as f:
    f.write(new_content)
print("Successfully patched src/mnemo_mcp/sync/delta.py")
