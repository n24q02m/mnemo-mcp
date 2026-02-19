"""Tests for mnemo_mcp.db with vector search enabled."""

import struct
from collections.abc import Generator
from pathlib import Path

import pytest

from mnemo_mcp.db import MemoryDB


@pytest.fixture
def vec_db(tmp_path: Path) -> Generator[MemoryDB]:
    """MemoryDB with vector search enabled (3 dimensions)."""
    db = MemoryDB(tmp_path / "vec_test.db", embedding_dims=3)
    yield db
    db.close()


@pytest.fixture
def vec_db_with_data(vec_db: MemoryDB) -> MemoryDB:
    """MemoryDB seeded with 3D vectors."""
    # v1: [1, 0, 0] - Tech
    vec_db.add(
        "Python programming",
        category="tech",
        embedding=[1.0, 0.0, 0.0],
    )
    # v2: [0, 1, 0] - Personal
    vec_db.add(
        "Buy groceries",
        category="personal",
        embedding=[0.0, 1.0, 0.0],
    )
    # v3: [0, 0, 1] - Work
    vec_db.add(
        "Meeting notes",
        category="work",
        embedding=[0.0, 0.0, 1.0],
    )
    # v4: [0.5, 0.5, 0] - Mixed (close to both tech and personal)
    vec_db.add(
        "Tech groceries",
        category="mixed",
        embedding=[0.5, 0.5, 0.0],
    )
    return vec_db


class TestVecEnabled:
    def test_vec_enabled_is_true(self, vec_db: MemoryDB):
        assert vec_db.vec_enabled is True

    def test_table_exists(self, vec_db: MemoryDB):
        row = vec_db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_vec'"
        ).fetchone()
        assert row is not None


class TestAddVec:
    def test_add_stores_embedding(self, vec_db: MemoryDB):
        embedding = [0.1, 0.2, 0.3]
        mid = vec_db.add("test", embedding=embedding)

        # Verify directly in memories_vec table
        row = vec_db._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is not None

        # Deserialize float array
        # sqlite-vec returns raw bytes for embedding column? Or serialized?
        # Actually, standard sqlite-vec returns the vector as a blob/bytes which matches input format?
        # Let's check what we get.
        stored_bytes = row[0]
        assert len(stored_bytes) == 12  # 3 floats * 4 bytes
        unpacked = struct.unpack("3f", stored_bytes)
        # Verify values are close (float precision)
        assert abs(unpacked[0] - 0.1) < 1e-6
        assert abs(unpacked[1] - 0.2) < 1e-6
        assert abs(unpacked[2] - 0.3) < 1e-6

    def test_add_without_embedding_skips_vec_table(self, vec_db: MemoryDB):
        mid = vec_db.add("no vec")
        row = vec_db._conn.execute(
            "SELECT * FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is None


class TestSearchVec:
    def test_exact_match(self, vec_db_with_data: MemoryDB):
        # Search with [1, 0, 0] -> Should find Python programming (tech)
        results = vec_db_with_data.search("irrelevant", embedding=[1.0, 0.0, 0.0])
        assert len(results) > 0
        top = results[0]
        assert "Python" in top["content"]
        assert top["category"] == "tech"
        # Score should be very high (distance ~ 0)
        # Note: hybrid score mixes FTS and Vector, but with "irrelevant" query, FTS score is 0.
        # So score comes purely from vector + recency + frequency.
        # Vector score should be 1.0 (max).

    def test_distance_ranking(self, vec_db_with_data: MemoryDB):
        # Search with [0.1, 0.9, 0] -> Should be closer to Personal [0, 1, 0] than Tech [1, 0, 0]
        results = vec_db_with_data.search("irrelevant", embedding=[0.1, 0.9, 0.0])

        # Find rank of Personal and Tech
        personal_idx = -1
        tech_idx = -1

        for i, r in enumerate(results):
            if r["category"] == "personal":
                personal_idx = i
            elif r["category"] == "tech":
                tech_idx = i

        assert personal_idx != -1
        assert tech_idx != -1
        assert personal_idx < tech_idx  # Personal should be ranked higher (lower index)

    def test_category_filter(self, vec_db_with_data: MemoryDB):
        # Search with [1, 0, 0] (Tech vector) but filter for 'personal'
        # Should NOT return the Tech memory, should return Personal memory (if close enough)
        results = vec_db_with_data.search(
            "irrelevant",
            embedding=[1.0, 0.0, 0.0],
            category="personal"
        )

        # Should verify no 'tech' category in results
        assert all(r["category"] == "personal" for r in results)

        # Should find the personal memory because it matches category, even if vector is far
        # (It's still returned if within limit)
        assert any(r["category"] == "personal" for r in results)

    def test_category_filter_empty(self, vec_db_with_data: MemoryDB):
        # Filter for non-existent category
        results = vec_db_with_data.search(
            "irrelevant",
            embedding=[1.0, 0.0, 0.0],
            category="ghost"
        )
        assert len(results) == 0

    def test_hybrid_ranking(self, vec_db_with_data: MemoryDB):
        # Query matches "Python" (tech) and Vector matches [1, 0, 0] (tech)
        # Should be overwhelming winner
        results = vec_db_with_data.search("Python", embedding=[1.0, 0.0, 0.0])
        assert results[0]["category"] == "tech"

    def test_vector_only_search(self, vec_db_with_data: MemoryDB):
        # Search with empty string but valid vector
        results = vec_db_with_data.search("", embedding=[0.0, 0.0, 1.0])
        # Should find Work [0, 0, 1]
        assert results[0]["category"] == "work"


class TestUpdateVec:
    def test_update_embedding(self, vec_db: MemoryDB):
        # Add with [1, 0, 0]
        mid = vec_db.add("test", embedding=[1.0, 0.0, 0.0])

        # Update to [0, 1, 0]
        vec_db.update(mid, embedding=[0.0, 1.0, 0.0])

        # Verify in DB
        row = vec_db._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        unpacked = struct.unpack("3f", row[0])
        assert abs(unpacked[0] - 0.0) < 1e-6
        assert abs(unpacked[1] - 1.0) < 1e-6


class TestDeleteVec:
    def test_delete_removes_embedding(self, vec_db: MemoryDB):
        mid = vec_db.add("test", embedding=[1.0, 0.0, 0.0])
        vec_db.delete(mid)

        row = vec_db._conn.execute(
            "SELECT * FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is None
