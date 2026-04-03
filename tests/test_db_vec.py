"""Tests for mnemo_mcp.db with vector search enabled."""

import struct
from pathlib import Path

import pytest

from mnemo_mcp.db import MemoryDB


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize float list to bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def tmp_db_vec(tmp_path: Path):
    """Temporary MemoryDB with vector search enabled."""
    db = MemoryDB(tmp_path / "test_vec.db", embedding_dims=3)
    yield db
    db.close()


class TestVecEnabled:
    def test_vec_enabled(self, tmp_db_vec):
        assert tmp_db_vec.vec_enabled is True


class TestUpdateWithVectors:
    def test_add_stores_embedding(self, tmp_db_vec):
        emb = [0.1, 0.2, 0.3]
        mid = tmp_db_vec.add("test", embedding=emb)

        row = tmp_db_vec._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is not None
        assert row["embedding"] == _serialize_f32(emb)

    def test_update_replaces_embedding(self, tmp_db_vec):
        emb1 = [0.1, 0.0, 0.0]
        mid = tmp_db_vec.add("test", embedding=emb1)

        emb2 = [0.0, 1.0, 0.0]
        tmp_db_vec.update(mid, embedding=emb2)

        row = tmp_db_vec._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is not None
        assert row["embedding"] == _serialize_f32(emb2)

    def test_update_preserves_embedding_when_none_provided(self, tmp_db_vec):
        emb = [0.1, 0.0, 0.0]
        mid = tmp_db_vec.add("test", embedding=emb)

        # Update content only, no embedding
        tmp_db_vec.update(mid, content="updated content")

        row = tmp_db_vec._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is not None
        assert row["embedding"] == _serialize_f32(emb)

        mem = tmp_db_vec.get(mid)
        assert mem["content"] == "updated content"

    def test_update_embedding_only(self, tmp_db_vec):
        emb1 = [0.1, 0.0, 0.0]
        mid = tmp_db_vec.add("test", embedding=emb1)

        emb2 = [0.0, 0.0, 1.0]
        tmp_db_vec.update(mid, embedding=emb2)

        row = tmp_db_vec._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is not None
        assert row["embedding"] == _serialize_f32(emb2)

        mem = tmp_db_vec.get(mid)
        assert mem["content"] == "test"

    def test_delete_removes_embedding(self, tmp_db_vec):
        emb = [0.1, 0.2, 0.3]
        mid = tmp_db_vec.add("test", embedding=emb)

        tmp_db_vec.delete(mid)

        row = tmp_db_vec._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is None

    def test_update_ignores_empty_embedding_list(self, tmp_db_vec):
        """Passing an empty list for embedding should not trigger update logic."""
        emb = [0.1, 0.0, 0.0]
        mid = tmp_db_vec.add("test", embedding=emb)

        # Empty list is falsy, so it should behave like None
        tmp_db_vec.update(mid, embedding=[])

        row = tmp_db_vec._conn.execute(
            "SELECT embedding FROM memories_vec WHERE id = ?", (mid,)
        ).fetchone()
        assert row is not None
        assert row["embedding"] == _serialize_f32(emb)


class TestVecAutoDetection:
    def test_detects_dimensions_from_existing_db(self, tmp_path):
        db_path = tmp_path / "detect.db"
        # 1. Create DB with 123 dims
        db1 = MemoryDB(db_path, embedding_dims=123)
        assert db1.embedding_dims == 123
        db1.close()

        # 2. Re-open with different requested dims (e.g., 0 or 768)
        # It should detect 123 from the table.
        db2 = MemoryDB(db_path, embedding_dims=768)
        assert db2.embedding_dims == 123
        db2.close()

    def test_detects_dimensions_with_zero_initial_request(self, tmp_path):
        db_path = tmp_path / "detect_zero.db"
        # 1. Create DB with 64 dims
        db1 = MemoryDB(db_path, embedding_dims=64)
        assert db1.embedding_dims == 64
        db1.close()

        # 2. Re-open with 0 dims (auto-detect)
        # Even if 0 is passed, it should detect 64 and enable vectors.
        db2 = MemoryDB(db_path, embedding_dims=0)
        assert db2.embedding_dims == 64
        assert db2.vec_enabled is True
        db2.close()
