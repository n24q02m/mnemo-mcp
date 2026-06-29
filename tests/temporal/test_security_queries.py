from mnemo_mcp.db import MemoryDB
from mnemo_mcp.graph import link_memory_entities, upsert_entities
from mnemo_mcp.temporal.queries import entity_graph, entity_search


def test_entity_search_injection_safe(tmp_db: MemoryDB):
    # Seed some data
    mid = tmp_db.add("Security content")
    eids = upsert_entities(tmp_db._conn, [{"name": "SecureEntity", "type": "concept"}])
    link_memory_entities(tmp_db._conn, mid, eids)
    tmp_db._conn.commit()

    # Normal search
    results = entity_search(tmp_db, name="SecureEntity")
    assert len(results) == 1
    assert results[0]["id"] == mid


def test_entity_graph_injection_safe(tmp_db: MemoryDB):
    mid = tmp_db.add("Graph content")
    eids = upsert_entities(
        tmp_db._conn,
        [{"name": "A", "type": "concept"}, {"name": "B", "type": "concept"}],
    )
    link_memory_entities(tmp_db._conn, mid, eids)
    tmp_db._conn.commit()

    # entity_graph uses name to resolve ID first
    result = entity_graph(tmp_db, name="A")
    assert len(result["nodes"]) >= 1
    assert any(n["name"] == "A" for n in result["nodes"])


def test_entity_search_with_many_entities(tmp_db: MemoryDB):
    # This might trigger issues if placeholders generation was used
    entities = [{"name": f"E{i}", "type": "concept"} for i in range(100)]
    mid = tmp_db.add("Massive entities")
    eids = upsert_entities(tmp_db._conn, entities)
    link_memory_entities(tmp_db._conn, mid, eids)
    tmp_db._conn.commit()

    results = entity_search(tmp_db, name="E0")
    assert len(results) >= 1
