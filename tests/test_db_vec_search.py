import json
from pathlib import Path

import pytest

from mnemo_mcp.db import MemoryDB


@pytest.fixture
def vec_db(tmp_path: Path):
    """MemoryDB with vector search enabled (dims=4)."""
    db = MemoryDB(tmp_path / "vec_test.db", embedding_dims=4)
    if not db.vec_enabled:
        pytest.skip("sqlite-vec not available")
    yield db
    db.close()

def test_vector_search_basic(vec_db: MemoryDB):
    # Add memories with embeddings
    # Target memory: close to [0.1, 0.1, 0.1, 0.1]
    vec_db.add("target", embedding=[0.1, 0.1, 0.1, 0.1])
    # Distant memory
    vec_db.add("distant", embedding=[0.9, 0.9, 0.9, 0.9])

    # Search near target
    results = vec_db.search("target", embedding=[0.1, 0.1, 0.1, 0.1])

    assert len(results) >= 1
    # First result should be the target
    assert results[0]["content"] == "target"
    # Should have score
    assert results[0]["score"] > 0
    # Should NOT have internal scores (cleaned up)
    assert "distance" not in results[0]
    assert "vec_score" not in results[0]

def test_vector_search_category_filter(vec_db: MemoryDB):
    # Add memories
    vec_db.add("general match", embedding=[0.1, 0.1, 0.1, 0.1], category="general")
    vec_db.add("work match", embedding=[0.1, 0.1, 0.1, 0.1], category="work")

    # Search with category 'work'
    results = vec_db.search("match", embedding=[0.1, 0.1, 0.1, 0.1], category="work")

    # Should only find 'work match'
    assert len(results) == 1
    assert results[0]["content"] == "work match"

def test_vector_search_returns_columns(vec_db: MemoryDB):
    """Verify that columns from 'memories' table are correctly returned."""
    vec_db.add(
        "rich memory",
        embedding=[0.5]*4,
        category="special",
        tags=["t1", "t2"],
        source="unit-test"
    )

    results = vec_db.search("rich", embedding=[0.5]*4)
    assert len(results) >= 1
    mem = results[0]

    assert mem["content"] == "rich memory"
    assert mem["category"] == "special"
    assert json.loads(mem["tags"]) == ["t1", "t2"]
    assert mem["source"] == "unit-test"
    assert "created_at" in mem
    assert "updated_at" in mem

def test_vector_search_no_match_query(vec_db: MemoryDB):
    """Search with vector but no text match should still return vector results."""
    vec_db.add("text mismatch", embedding=[0.2]*4)

    # FTS won't match "nomatch", but vector might be close
    # Wait, Hybrid search merges results. If FTS returns nothing, but Vector returns something.
    results = vec_db.search("nomatch", embedding=[0.2]*4)

    assert len(results) >= 1
    assert results[0]["content"] == "text mismatch"
