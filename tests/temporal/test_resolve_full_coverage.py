"""Full coverage tests for mnemo_mcp.temporal.resolve."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest
import sqlite_vec

from mnemo_mcp.db import MemoryDB
from mnemo_mcp.temporal.resolve import (
    _serialize,
    find_similar_entity,
    insert_entity_with_embedding,
)

# Skip all tests in this module when SQLite was compiled without
# loadable-extensions support (macOS default).
_test_conn = sqlite3.connect(":memory:")
_HAS_LOAD_EXT = hasattr(_test_conn, "enable_load_extension")
_test_conn.close()
if _HAS_LOAD_EXT:
    try:
        _test_conn = sqlite3.connect(":memory:")
        _test_conn.enable_load_extension(True)
        _test_conn.close()
    except (AttributeError, sqlite3.NotSupportedError):
        _HAS_LOAD_EXT = False

pytestmark = pytest.mark.skipif(
    not _HAS_LOAD_EXT,
    reason="SQLite loadable extensions not enabled (macOS default).",
)


def _setup_vec(db: MemoryDB) -> None:
    db._conn.enable_load_extension(True)
    sqlite_vec.load(db._conn)
    db._conn.enable_load_extension(False)
    db._conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS memory_entities_vec "
        "USING vec0(embedding float[768])"
    )
    db._conn.commit()


@pytest.fixture
def db_with_vec(tmp_path):
    db = MemoryDB(tmp_path / "test.db", embedding_dims=768)
    _setup_vec(db)
    yield db
    db.close()


def test_serialize_padding():
    # Test line 53: padding shorter vectors
    short_vec = [1.0, 2.0]
    serialized = _serialize(short_vec)
    assert len(serialized) == 768 * 4  # 768 floats * 4 bytes

    # Test line 55: truncating longer vectors
    long_vec = [1.0] * 1000
    serialized_long = _serialize(long_vec)
    assert len(serialized_long) == 768 * 4


def test_insert_entity_with_embedding_missing_rowid(db_with_vec: MemoryDB):
    # Test line 167->185: ent_rowid is None
    # We can simulate this by mocking the connection to return None for the rowid query
    mock_conn = MagicMock(wraps=db_with_vec._conn)

    def mock_execute(sql, *args):
        if "SELECT rowid FROM memory_entities WHERE id = ?" in sql:
            return MagicMock(fetchone=lambda: None)
        return db_with_vec._conn.execute(sql, *args)

    mock_conn.execute.side_effect = mock_execute

    eid = insert_entity_with_embedding(mock_conn, "Ghost", "concept", [0.1] * 768)
    assert eid
    # No embedding should have been inserted
    count = db_with_vec._conn.execute(
        "SELECT COUNT(*) FROM memory_entities_vec"
    ).fetchone()[0]
    assert count == 0


def test_insert_entity_with_embedding_exception(db_with_vec: MemoryDB):
    # Test line 181-183: exception during embedding insert
    mock_conn = MagicMock(wraps=db_with_vec._conn)

    def mock_execute(sql, *args):
        if "INSERT INTO memory_entities_vec" in sql:
            raise Exception("SIMULATED INSERT FAILURE")
        return db_with_vec._conn.execute(sql, *args)

    mock_conn.execute.side_effect = mock_execute

    eid = insert_entity_with_embedding(mock_conn, "Failure", "concept", [0.1] * 768)
    assert eid
    # Should still commit the entity
    count = db_with_vec._conn.execute(
        "SELECT COUNT(*) FROM memory_entities WHERE name = 'Failure'"
    ).fetchone()[0]
    assert count == 1


def test_find_similar_entity_default_threshold(db_with_vec: MemoryDB):
    # Test line 88: threshold is None
    v = [0.1] * 768
    insert_entity_with_embedding(db_with_vec._conn, "Base", "concept", v)

    # This should use default threshold 0.85
    eid = find_similar_entity(
        db_with_vec._conn, "Similar", "concept", v, threshold=None
    )
    assert eid is not None
