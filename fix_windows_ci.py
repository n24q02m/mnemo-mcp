<<<<<<< SEARCH
    if ents:
        try:
            # Bolt Performance Optimization:
            # Use json_each to prevent N+1 SQLite query overhead while
            # maintaining reliable rowcount for sync stats.
            cursor.execute(
                """INSERT OR IGNORE INTO memory_entities
                (id, name, entity_type, created_at, updated_at)
                SELECT
                    json_extract(value, '$.id'),
                    json_extract(value, '$.name'),
                    json_extract(value, '$.entity_type'),
                    json_extract(value, '$.created_at'),
                    json_extract(value, '$.updated_at')
                FROM json_each(?)""",
                (json.dumps(ents),),
            )
            counts["entities_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: entities bulk skipped ({e})")
=======
    if ents:
        try:
            # Bolt Performance Optimization:
            # Use json_each to prevent N+1 SQLite query overhead while
            # maintaining reliable rowcount for sync stats.
            cursor.execute(
                """INSERT OR IGNORE INTO memory_entities
                (id, name, entity_type, created_at, updated_at)
                SELECT
                    json_extract(value, '$.id'),
                    json_extract(value, '$.name'),
                    json_extract(value, '$.entity_type'),
                    json_extract(value, '$.created_at'),
                    json_extract(value, '$.updated_at')
                FROM json_each(?)""",
                (json.dumps(ents),),
            )
            counts["entities_applied"] = cursor.rowcount or 0
            # Explicitly commit here to reduce transaction scope and avoid
            # "database disk image is malformed" on Windows during bulk writes.
            db._conn.commit()
        except Exception as e:
            logger.debug(f"apply_bundle: entities bulk skipped ({e})")
>>>>>>> REPLACE
<<<<<<< SEARCH
    if edges:
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO memory_edges
                (id, source_id, target_id, relation_type, created_at,
                 memory_id, valid_from, valid_to)
                SELECT
                    json_extract(value, '$.id'),
                    json_extract(value, '$.source_id'),
                    json_extract(value, '$.target_id'),
                    json_extract(value, '$.relation_type'),
                    json_extract(value, '$.created_at'),
                    json_extract(value, '$.memory_id'),
                    json_extract(value, '$.valid_from'),
                    json_extract(value, '$.valid_to')
                FROM json_each(?)""",
                (json.dumps(edges),),
            )
            counts["edges_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: edges bulk skipped ({e})")
=======
    if edges:
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO memory_edges
                (id, source_id, target_id, relation_type, created_at,
                 memory_id, valid_from, valid_to)
                SELECT
                    json_extract(value, '$.id'),
                    json_extract(value, '$.source_id'),
                    json_extract(value, '$.target_id'),
                    json_extract(value, '$.relation_type'),
                    json_extract(value, '$.created_at'),
                    json_extract(value, '$.memory_id'),
                    json_extract(value, '$.valid_from'),
                    json_extract(value, '$.valid_to')
                FROM json_each(?)""",
                (json.dumps(edges),),
            )
            counts["edges_applied"] = cursor.rowcount or 0
            db._conn.commit()
        except Exception as e:
            logger.debug(f"apply_bundle: edges bulk skipped ({e})")
>>>>>>> REPLACE
<<<<<<< SEARCH
    if links:
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO memory_entity_links
                (memory_id, entity_id)
                SELECT
                    json_extract(value, '$.memory_id'),
                    json_extract(value, '$.entity_id')
                FROM json_each(?)""",
                (json.dumps(links),),
            )
            counts["links_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: links bulk skipped ({e})")

    db._conn.commit()
    return counts
=======
    if links:
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO memory_entity_links
                (memory_id, entity_id)
                SELECT
                    json_extract(value, '$.memory_id'),
                    json_extract(value, '$.entity_id')
                FROM json_each(?)""",
                (json.dumps(links),),
            )
            counts["links_applied"] = cursor.rowcount or 0
            db._conn.commit()
        except Exception as e:
            logger.debug(f"apply_bundle: links bulk skipped ({e})")

    return counts
>>>>>>> REPLACE
