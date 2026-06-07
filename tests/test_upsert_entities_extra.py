import pytest
from datetime import datetime
from mnemo_mcp.db import MemoryDB
from mnemo_mcp.graph import upsert_entities

class TestUpsertEntitiesExtra:
    def test_upsert_batching_logic(self, tmp_db: MemoryDB):
        """Test batching logic by upserting more than 400 unique entities."""
        conn = tmp_db._conn
        # Use enough entities to ensure the BATCH_SIZE=400 loop is exercised
        count = 450
        entities = [{"name": f"BatchEntity {i}", "type": "concept"} for i in range(count)]
        ids = upsert_entities(conn, entities)

        assert len(ids) == count, f"Expected {count} IDs, got {len(ids)}"
        assert all(isinstance(i, str) for i in ids), f"Not all IDs are strings: {ids[:5]}"
        assert len(set(ids)) == count, "All IDs should be unique for unique entities"

    def test_upsert_id_stability_and_timestamps(self, tmp_db: MemoryDB):
        """Verify ID stability and that timestamps are set correctly without fragile mocking."""
        conn = tmp_db._conn
        name, etype = "StabilityTest", "concept"
        entity = {"name": name, "type": etype}

        # First upsert
        ids1 = upsert_entities(conn, [entity])
        assert len(ids1) == 1
        id1 = ids1[0]
        assert isinstance(id1, str)

        row1 = conn.execute(
            "SELECT created_at, updated_at FROM memory_entities WHERE id = ?", (id1,)
        ).fetchone()
        assert row1 is not None
        c1, u1 = row1["created_at"], row1["updated_at"]

        # Second upsert (conflict)
        ids2 = upsert_entities(conn, [entity])
        assert len(ids2) == 1
        id2 = ids2[0]

        assert id1 == id2, f"ID must be stable on conflict: {id1} vs {id2}"

        row2 = conn.execute(
            "SELECT created_at, updated_at FROM memory_entities WHERE id = ?", (id2,)
        ).fetchone()
        assert row2 is not None
        c2, u2 = row2["created_at"], row2["updated_at"]

        assert c1 == c2, "created_at should not change on conflict"
        # Verify valid ISO format
        try:
            datetime.fromisoformat(c1)
            datetime.fromisoformat(u2)
        except ValueError as e:
            pytest.fail(f"Invalid ISO format in DB: {e}")

    def test_upsert_updates_timestamp_on_conflict(self, tmp_db: MemoryDB):
        """Explicitly verify updated_at changes on conflict."""
        conn = tmp_db._conn
        entity = {"name": "TimestampTest", "type": "concept"}

        # Initial insert
        ids1 = upsert_entities(conn, [entity])
        id1 = ids1[0]

        old_ts = "2020-01-01T00:00:00+00:00"
        conn.execute(
            "UPDATE memory_entities SET updated_at = ? WHERE id = ?", (old_ts, id1)
        )
        conn.commit()

        # Upsert again
        upsert_entities(conn, [entity])

        row = conn.execute(
            "SELECT updated_at FROM memory_entities WHERE id = ?", (id1,)
        ).fetchone()
        assert row["updated_at"] != old_ts, "updated_at should have been updated by UPSERT"

    def test_entities_same_name_different_type(self, tmp_db: MemoryDB):
        """Entities with same name but different types should be distinct."""
        conn = tmp_db._conn
        entities = [
            {"name": "Python", "type": "tool"},
            {"name": "Python", "type": "language"},
        ]
        ids = upsert_entities(conn, entities)
        assert len(ids) == 2, f"Expected 2 IDs, got {len(ids)}"
        assert ids[0] != ids[1], f"IDs should be different for different types: {ids[0]}"

        rows = conn.execute(
            "SELECT id, entity_type FROM memory_entities WHERE name = 'Python' ORDER BY entity_type"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0]["entity_type"] == "language"
        assert rows[1]["entity_type"] == "tool"

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
        # upsert_entities skips invalid ones and returns IDs only for valid ones
        assert len(ids) == 2

        names = [r["name"] for r in conn.execute("SELECT name FROM memory_entities").fetchall()]
        assert "Valid1" in names
        assert "Valid2" in names
        assert "" not in names
