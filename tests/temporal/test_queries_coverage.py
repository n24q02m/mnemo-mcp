from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from mnemo_mcp.db import MemoryDB
from mnemo_mcp.graph import (
    create_relations,
    link_memory_entities,
    upsert_entities,
)
from mnemo_mcp.temporal.queries import (
    entity_graph,
    entity_search,
    history_for_entity,
    memories_as_of,
)

def _seed_kg(db: MemoryDB, content: str, entities, relations=None):
    mid = db.add(content)
    eids = upsert_entities(db._conn, entities)
    name_to_id = {}
    for ent, eid in zip(entities, eids, strict=False):
        name_to_id[ent["name"]] = eid
    if relations:
        create_relations(db._conn, relations, name_to_id)
    link_memory_entities(db._conn, mid, eids)
    db._conn.commit()
    return mid, name_to_id

def test_history_for_entity_ordering(tmp_db: MemoryDB):
    # m1: created_at = 2020, valid_from = NULL
    # m2: created_at = 2021, valid_from = 2021-01-01
    # m3: created_at = 2022, valid_from = 2019-01-01 (should be first)

    mid1, ents = _seed_kg(tmp_db, "m1", [{"name": "E", "type": "concept"}])
    eid = ents["E"]
    tmp_db._conn.execute("UPDATE memories SET created_at = '2020-01-01T00:00:00', valid_from = NULL WHERE id = ?", (mid1,))

    mid2, _ = _seed_kg(tmp_db, "m2", [{"name": "E", "type": "concept"}])
    tmp_db._conn.execute("UPDATE memories SET created_at = '2021-01-01T00:00:00', valid_from = '2021-01-01T00:00:00' WHERE id = ?", (mid2,))

    mid3, _ = _seed_kg(tmp_db, "m3", [{"name": "E", "type": "concept"}])
    tmp_db._conn.execute("UPDATE memories SET created_at = '2022-01-01T00:00:00', valid_from = '2019-01-01T00:00:00' WHERE id = ?", (mid3,))

    tmp_db._conn.commit()

    history = history_for_entity(tmp_db, eid)
    ids = [m["id"] for m in history]
    # Expected order: mid3 (2019), mid1 (2020), mid2 (2021)
    assert ids == [mid3, mid1, mid2]

def test_history_for_entity_superseded(tmp_db: MemoryDB):
    mid, ents = _seed_kg(tmp_db, "superseded", [{"name": "E", "type": "concept"}])
    eid = ents["E"]
    tmp_db._conn.execute("UPDATE memories SET valid_to = '2023-01-01T00:00:00' WHERE id = ?", (mid,))
    tmp_db._conn.commit()

    history = history_for_entity(tmp_db, eid)
    assert len(history) == 1
    assert history[0]["id"] == mid

def test_history_for_entity_empty(tmp_db: MemoryDB):
    assert history_for_entity(tmp_db, "non-existent-id") == []

def test_entity_search_limit_clamping(tmp_db: MemoryDB):
    _seed_kg(tmp_db, "content", [{"name": "E", "type": "concept"}])
    # limit < 1 -> 1
    res1 = entity_search(tmp_db, name="E", limit=0)
    assert len(res1) == 1
    # limit > 100 -> 100
    res2 = entity_search(tmp_db, name="E", limit=1000)
    assert len(res2) == 1
    # limit not int -> skips clamping
    res3 = entity_search(tmp_db, name="E", limit="1")
    assert len(res3) == 1

def test_entity_graph_name_resolution(tmp_db: MemoryDB):
    # Unknown entity by name
    res1 = entity_graph(tmp_db, name="Unknown")
    assert res1["anchor"] == "Unknown"
    assert res1["nodes"] == []

    # Known entity by name
    _, ents = _seed_kg(tmp_db, "content", [{"name": "Known", "type": "concept"}])
    eid = ents["Known"]
    res2 = entity_graph(tmp_db, name="Known")
    assert res2["anchor"] == eid

def test_entity_graph_no_nodes(tmp_db: MemoryDB, monkeypatch):
    mock_db = MagicMock(spec=MemoryDB)
    mock_db._conn = MagicMock()
    mock_db._conn.execute.return_value.fetchall.return_value = []

    # Case where entity_id is provided but BFS returns nothing
    res = entity_graph(mock_db, entity_id="some-id")
    assert res["nodes"] == []
    assert res["anchor"] == "some-id"

def test_memories_as_of_limit_clamping(tmp_db: MemoryDB):
    tmp_db.add("content")
    tmp_db._conn.execute("UPDATE memories SET valid_from = '2020-01-01T00:00:00' WHERE id = (SELECT id FROM memories LIMIT 1)")
    tmp_db._conn.commit()

    # limit < 1 -> 1
    res1 = memories_as_of(tmp_db, limit=0)
    assert len(res1) == 1
    # limit > 100 -> 100
    res2 = memories_as_of(tmp_db, limit=1000)
    assert len(res2) == 1
    # limit not int -> skips clamping
    res3 = memories_as_of(tmp_db, limit="1")
    assert len(res3) == 1
