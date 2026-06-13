import pytest

from mnemo_mcp.db import MemoryDB


def test_rrf_fuse_empty():
    """Test RRF fusion with empty lists."""
    assert MemoryDB.rrf_fuse([], []) == []


def test_rrf_fuse_single_list():
    """Test RRF fusion when only one list has results."""
    # k=60 (default)
    # rank 1 score: 1 / (60 + 1) = 1/61
    results = MemoryDB.rrf_fuse(["a"], [])
    assert results == [("a", 1 / 61)]

    results = MemoryDB.rrf_fuse([], ["b"])
    assert results == [("b", 1 / 61)]


def test_rrf_fuse_non_overlapping():
    """Test RRF fusion with non-overlapping result sets."""
    # fts: a (rank 1) -> 1/61
    # vec: b (rank 1) -> 1/61
    results = MemoryDB.rrf_fuse(["a"], ["b"])
    # Sort order for same score is stable by input order in dict,
    # but we should check the content.
    assert set(results) == {("a", 1 / 61), ("b", 1 / 61)}


def test_rrf_fuse_overlapping():
    """Test RRF fusion with overlapping result sets."""
    # fts: a (1), b (2)
    # vec: b (1), c (2)
    # a: 1/(60+1) = 1/61
    # b: 1/(60+2) + 1/(60+1) = 1/62 + 1/61
    # c: 1/(60+2) = 1/62
    results = MemoryDB.rrf_fuse(["a", "b"], ["b", "c"])
    assert results[0][0] == "b"
    assert results[0][1] == pytest.approx(1 / 61 + 1 / 62)
    assert results[1][0] == "a"
    assert results[1][1] == pytest.approx(1 / 61)
    assert results[2][0] == "c"
    assert results[2][1] == pytest.approx(1 / 62)


def test_rrf_fuse_custom_k():
    """Test RRF fusion with a custom k value."""
    # k=10
    # a: 1/(10+1) + 1/(10+1) = 2/11
    results = MemoryDB.rrf_fuse(["a"], ["a"], k=10)
    assert results == [("a", 2 / 11)]


def test_rrf_fuse_ranking_order():
    """Test RRF fusion ranking order logic."""
    fts = ["a", "b", "c"]
    vec = ["c", "b", "a"]
    # a: 1/61 + 1/63
    # b: 1/62 + 1/62 = 2/62
    # c: 1/63 + 1/61
    # 1/61 + 1/63 > 2/62
    results = MemoryDB.rrf_fuse(fts, vec)
    assert len(results) == 3
    assert results[0][0] in ("a", "c")
    assert results[1][0] in ("a", "c")
    assert results[2][0] == "b"
    assert results[0][1] == results[1][1]
    assert results[0][1] > results[2][1]
