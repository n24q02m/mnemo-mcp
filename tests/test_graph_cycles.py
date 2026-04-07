from mnemo_mcp.db import MemoryDB
from mnemo_mcp.graph import (
    create_relations,
    find_related_memory_ids,
    link_memory_entities,
    upsert_entities,
)


def test_graph_traversal_with_cycles(tmp_db: MemoryDB):
    """Test that graph traversal handles cycles correctly."""
    conn = tmp_db._conn
    mid1 = tmp_db.add("Memory 1")
    mid2 = tmp_db.add("Memory 2")

    ent_a = upsert_entities(conn, [{"name": "A", "type": "concept"}])
    ent_b = upsert_entities(conn, [{"name": "B", "type": "concept"}])

    link_memory_entities(conn, mid1, ent_a)
    link_memory_entities(conn, mid2, ent_b)

    # Cycle: A <-> B
    name_to_id = {"A": ent_a[0], "B": ent_b[0]}
    create_relations(
        conn,
        [
            {"source": "A", "target": "B", "type": "related_to"},
            {"source": "B", "target": "A", "type": "related_to"},
        ],
        name_to_id,
    )

    related = find_related_memory_ids(conn, mid1, max_depth=5)
    assert mid2 in related
