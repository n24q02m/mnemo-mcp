import sqlite3
import pytest
from mnemo_mcp.db import MemoryDB

class WrappedConnection:
    def __init__(self, conn):
        self._conn = conn
        self.call_count = 0
        self.queries = []

    def execute(self, sql, params=()):
        self.call_count += 1
        self.queries.append(sql)
        return self._conn.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._conn, name)

def test_search_performance(tmp_path):
    """Verify search does not have N+1 query issue."""
    db_path = tmp_path / "perf.db"
    # Enable vector search with 3 dims
    db = MemoryDB(db_path, embedding_dims=3)

    if not db.vec_enabled:
        pytest.skip("sqlite-vec not enabled/available")

    # Insert 10 memories with embeddings
    for i in range(10):
        db.add(
            f"unique content {i}",
            embedding=[0.1, 0.1, 0.1],
            tags=["tag"]
        )

    # Wrap the connection to count queries
    wrapped_conn = WrappedConnection(db._conn)
    db._conn = wrapped_conn

    # Search with embedding
    results = db.search(
        query="nomatch",
        embedding=[0.1, 0.1, 0.1],
        limit=10
    )

    assert len(results) == 10

    # We expect:
    # 1. FTS query (returns 0)
    # 2. Vector search query (returns 10, including all data)
    # Total = 2 queries.
    # Definitely NOT 12 queries.

    print(f"Total queries: {wrapped_conn.call_count}")
    for q in wrapped_conn.queries:
        print(f"Query: {q}")

    # Expected: 1 FTS + 1 Vector + 1 Update access_count = 3
    assert wrapped_conn.call_count <= 3, f"Expected <= 3 queries, got {wrapped_conn.call_count}"

    db.close()
