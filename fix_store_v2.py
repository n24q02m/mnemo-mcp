import sys

content = open("src/mnemo_mcp/temporal/store.py").read()

start_marker = "    edge_count = 0"
end_marker = "    logger.debug("

start_idx = content.find(start_marker, content.find("link_memory_entities"))
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f"Markers not found: start={start_idx}, end={end_idx}")
    sys.exit(1)

replacement = """    # Phase 3: backfill memory_id + valid_from on the freshly inserted edges.
    # We target rows that match (source, target, type) for this batch and
    # have NULL memory_id / NULL valid_from -- so an edge already attached
    # to an earlier capture is left alone.
    edge_count = 0
    if relations:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        # Deduplicate relations in Python to ensure accurate edge_count
        # (original loop would over-count if LLM produced redundant triples).
        seen_rels = set()
        unique_rels = []
        for rel in relations:
            src_id = name_to_id.get(rel.get("source", "").strip())
            tgt_id = name_to_id.get(rel.get("target", "").strip())
            rtype = rel.get("type", "").strip().lower()
            if src_id and tgt_id and rtype:
                key = (src_id, tgt_id, rtype)
                if key not in seen_rels:
                    seen_rels.add(key)
                    unique_rels.append(key)

        # Bolt Performance Optimization:
        # Replaced N+1 single-row UPDATEs with batched UPDATE + IN (VALUES ...)
        # to eliminate SQLite VM overhead while preserving reliable row counting.
        # We use BATCH_SIZE=100 to stay well under SQLITE_MAX_VARIABLE_NUMBER.
        BATCH_SIZE = 100
        for i in range(0, len(unique_rels), BATCH_SIZE):
            batch = unique_rels[i : i + BATCH_SIZE]
            placeholders = ", ".join(["(?, ?, ?)"] * len(batch))
            params = [memory_id, now_iso]
            for r_src, r_tgt, r_type in batch:
                params.extend([r_src, r_tgt, r_type])

            cursor = conn.execute(
                "UPDATE memory_edges SET "
                "  memory_id = COALESCE(memory_id, ?), "
                "  valid_from = COALESCE(valid_from, ?) "
                f"WHERE (source_id, target_id, relation_type) IN (VALUES {placeholders})",
                params,
            )
            edge_count += cursor.rowcount or 0
        conn.commit()

"""

new_content = content[:start_idx] + replacement + content[end_idx:]
with open("src/mnemo_mcp/temporal/store.py", "w") as f:
    f.write(new_content)
