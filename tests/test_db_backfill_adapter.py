from __future__ import annotations

from mnemo_mcp.db import MemoryDB


def test_rows_without_vectors_and_write_vector_round_trip(tmp_path):
    db = MemoryDB(tmp_path / "backfill.db", embedding_dims=3)
    first_id = db.add("first")
    second_id = db.add("second", embedding=[0.1, 0.2, 0.3])

    rows = db.rows_without_vectors(limit=10)

    assert [row["id"] for row in rows] == [first_id]

    db.write_vector(first_id, [0.4, 0.5, 0.6])

    assert db.rows_without_vectors(limit=10) == []
    assert db.stats()["total_memories"] == 2
    assert second_id != first_id


def test_rows_without_vectors_supports_excluding_seen_ids(tmp_path):
    db = MemoryDB(tmp_path / "backfill-exclude.db", embedding_dims=3)
    first_id = db.add("first")
    second_id = db.add("second")

    rows = db.rows_without_vectors(limit=10, exclude_ids={first_id})

    assert [row["id"] for row in rows] == [second_id]
