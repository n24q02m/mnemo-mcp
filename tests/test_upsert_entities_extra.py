from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from mnemo_mcp.db import MemoryDB
from mnemo_mcp.graph import upsert_entities


class TestUpsertEntitiesExtra:
    def test_upsert_batching_logic(self, tmp_db: MemoryDB):
        """Test batching logic by upserting more than 400 unique entities."""
        conn = tmp_db._conn
        # Create 401 unique entities to exceed BATCH_SIZE=400
        entities = [{"name": f"Entity {i}", "type": "concept"} for i in range(401)]
        ids = upsert_entities(conn, entities)
        assert len(ids) == 401
        assert len(set(ids)) == 401

        # Verify some entities from different batches
        row = conn.execute(
            "SELECT name FROM memory_entities WHERE name = 'Entity 0'"
        ).fetchone()
        assert row is not None
        row = conn.execute(
            "SELECT name FROM memory_entities WHERE name = 'Entity 399'"
        ).fetchone()
        assert row is not None
        row = conn.execute(
            "SELECT name FROM memory_entities WHERE name = 'Entity 400'"
        ).fetchone()
        assert row is not None

    def test_upsert_updates_timestamp_on_conflict(self, tmp_db: MemoryDB):
        """Verify that updated_at changes but id remains the same on conflict."""
        conn = tmp_db._conn
        entity = {"name": "ConflictTest", "type": "concept"}

        t1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        t2 = t1 + timedelta(seconds=1)

        with patch("mnemo_mcp.graph.datetime") as mock_datetime:
            mock_datetime.now.return_value = t1
            ids1 = upsert_entities(conn, [entity])

            mock_datetime.now.return_value = t2
            ids2 = upsert_entities(conn, [entity])

        assert ids1[0] == ids2[0]

        row = conn.execute(
            "SELECT created_at, updated_at FROM memory_entities WHERE id = ?",
            (ids1[0],),
        ).fetchone()
        assert row["created_at"] == t1.isoformat()
        assert row["updated_at"] == t2.isoformat()

    def test_entities_same_name_different_type(self, tmp_db: MemoryDB):
        """Entities with same name but different types should be distinct."""
        conn = tmp_db._conn
        entities = [
            {"name": "Python", "type": "tool"},
            {"name": "Python", "type": "language"},
        ]
        ids = upsert_entities(conn, entities)
        assert len(ids) == 2
        assert ids[0] != ids[1]

        rows = conn.execute(
            "SELECT entity_type FROM memory_entities WHERE name = 'Python'"
        ).fetchall()
        types = [r["entity_type"] for r in rows]
        assert "tool" in types
        assert "language" in types

    def test_mixed_valid_and_invalid_entities(self, tmp_db: MemoryDB):
        """Test with mixed valid and invalid (empty name) entities."""
        conn = tmp_db._conn
        entities = [
            {"name": "Valid1", "type": "concept"},
            {"name": "", "type": "concept"},
            {"name": "  ", "type": "concept"},
            {"name": "Valid2", "type": "tool"},
        ]
        ids = upsert_entities(conn, entities)
        assert len(ids) == 2

        rows = conn.execute("SELECT name FROM memory_entities").fetchall()
        names = [r["name"] for r in rows]
        assert "Valid1" in names
        assert "Valid2" in names
        assert "" not in names
        assert "  " not in names
