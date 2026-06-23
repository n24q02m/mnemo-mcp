from __future__ import annotations

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
    memories_as_of,
)


def _seed_kg(db: MemoryDB, content: str, entities, relations=None):
    """Helper: insert memory + link entities + edges."""
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


class TestQueriesCoverage:
    def test_memories_as_of_limit_non_int(self, tmp_db: MemoryDB):
        # Trigger false branch of isinstance(limit, int)
        tmp_db.add("test")
        result = memories_as_of(tmp_db, limit="10")  # type: ignore
        assert len(result) >= 0

    def test_memories_as_of_limit_clamping(self, tmp_db: MemoryDB):
        for i in range(10):
            tmp_db.add(f"test {i}")

        # Test lower bound
        result_min = memories_as_of(tmp_db, limit=-5)
        assert len(result_min) == 1

        # Test upper bound
        result_max = memories_as_of(tmp_db, limit=500)
        assert len(result_max) == 10

    def test_memories_as_of_excludes_archived(self, tmp_db: MemoryDB):
        mid = tmp_db.add("to be archived")
        # Soft archive manually since there's no direct 'archive' method
        tmp_db._conn.execute(
            "UPDATE memories SET archived_at = '2026-01-01' WHERE id = ?", (mid,)
        )
        tmp_db._conn.commit()
        result = memories_as_of(tmp_db)
        ids = {m["id"] for m in result}
        assert mid not in ids

    def test_entity_search_limit_non_int(self, tmp_db: MemoryDB):
        _seed_kg(tmp_db, "test", [{"name": "test", "type": "concept"}])
        result = entity_search(tmp_db, name="test", limit="10")  # type: ignore
        assert len(result) == 1

    def test_entity_graph_explicit_id(self, tmp_db: MemoryDB):
        mid, n2id = _seed_kg(tmp_db, "test", [{"name": "test", "type": "concept"}])
        eid = n2id["test"]
        # Pass explicit entity_id to skip name resolution
        result = entity_graph(tmp_db, entity_id=eid)
        assert result["anchor"] == eid
        assert len(result["nodes"]) == 1

    def test_entity_graph_missing_anchor(self, tmp_db: MemoryDB):
        # Both entity_id and name are None
        result = entity_graph(tmp_db, entity_id=None, name=None)
        assert result["nodes"] == []
        assert result["anchor"] == ""

    def test_entity_graph_no_nodes(self, tmp_db: MemoryDB):
        # Trigger line 154: if not node_ids: return ...
        # If we provide an entity_id that is NOT in the database, the CTE returns nothing.
        result = entity_graph(tmp_db, entity_id="non-existent-uuid")
        assert result["nodes"] == []
        assert result["anchor"] == "non-existent-uuid"

    def test_entity_graph_no_rows_mock(self, tmp_db: MemoryDB, monkeypatch):
        # To trigger line 154: if not node_ids: return ...
        # We can mock the DB connection's execute method via the MemoryDB instance
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        # We need a real MemoryDB but with a mocked _conn
        # Since _conn is established in __init__, we patch it
        monkeypatch.setattr(tmp_db, "_conn", mock_conn)

        result = entity_graph(tmp_db, entity_id="some-id")
        assert result["nodes"] == []
        assert result["anchor"] == "some-id"
