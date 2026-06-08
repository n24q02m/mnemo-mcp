import sys

with open("src/mnemo_mcp/sync/delta.py", "r") as f:
    content = f.read()

search_text = """    if ents_to_insert:
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
            logger.debug(f"apply_bundle: entities bulk insert failed ({e})")"""

replacement_text = """    if ents_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entities "
                "(id, name, entity_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ents_to_insert,
            )
            # Use rowcount to track actually applied (new) records.
            # Note: Although executemany rowcount can be a footgun in some contexts,
            # it is used here for sync convergence metrics, matching patterns in db.py.
            counts["entities_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: entities bulk insert failed ({e})")"""

content = content.replace(search_text, replacement_text)

search_text = """    if edges_to_insert:
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
            logger.debug(f"apply_bundle: edges bulk insert failed ({e})")"""

replacement_text = """    if edges_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_edges "
                "(id, source_id, target_id, relation_type, created_at, "
                " memory_id, valid_from, valid_to) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                edges_to_insert,
            )
            counts["edges_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: edges bulk insert failed ({e})")"""

content = content.replace(search_text, replacement_text)

search_text = """    if links_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entity_links "
                "(memory_id, entity_id) VALUES (?, ?)",
                links_to_insert,
            )
            counts["links_applied"] = len(links_to_insert)
        except Exception as e:
            logger.debug(f"apply_bundle: links bulk insert failed ({e})")"""

replacement_text = """    if links_to_insert:
        try:
            # Bolt Performance Optimization: Use executemany to prevent N+1 queries.
            cursor.executemany(
                "INSERT OR IGNORE INTO memory_entity_links "
                "(memory_id, entity_id) VALUES (?, ?)",
                links_to_insert,
            )
            counts["links_applied"] = cursor.rowcount or 0
        except Exception as e:
            logger.debug(f"apply_bundle: links bulk insert failed ({e})")"""

content = content.replace(search_text, replacement_text)

with open("src/mnemo_mcp/sync/delta.py", "w") as f:
    f.write(content)
print("Successfully patched src/mnemo_mcp/sync/delta.py")
