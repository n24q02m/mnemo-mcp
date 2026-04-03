import json

from mnemo_mcp.db import MemoryDB


def test_tag_filtering_json_each(tmp_db: MemoryDB):
    """Verify that tag filtering works with the new json_each implementation."""
    tmp_db.add("content 1", tags=["tag1", "tag2"])
    tmp_db.add("content 2", tags=["tag2", "tag3"])
    tmp_db.add("content 3", tags=["tag4"])

    # Search with one matching tag
    results = tmp_db.search("content", tags=["tag1"])
    assert len(results) == 1
    assert results[0]["content"] == "content 1"

    # Search with multiple tags (OR logic in EXISTS/json_each)
    results = tmp_db.search("content", tags=["tag1", "tag3"])
    assert len(results) == 2
    contents = {r["content"] for r in results}
    assert "content 1" in contents
    assert "content 2" in contents

    # Search with no matching tags
    results = tmp_db.search("content", tags=["nonexistent"])
    assert len(results) == 0


def test_tag_limit_validation(tmp_db: MemoryDB):
    """Verify that the tag list is truncated to 100 entries."""
    # Add a memory with a specific tag
    target_tag = "tag_999"
    tmp_db.add("content target", tags=[target_tag])

    # Create 101 tags. If it truncates to 100, and we put the target at 101, it shouldn't find it.
    many_tags = [f"other_{i}" for i in range(100)] + [target_tag]

    results = tmp_db.search("content", tags=many_tags)
    # It should have truncated to the first 100 "other_i" tags.
    assert len(results) == 0

    # If we put target_tag in the first 100, it should find it.
    many_tags_with_target = [target_tag] + [f"other_{i}" for i in range(100)]
    results = tmp_db.search("content", tags=many_tags_with_target)
    assert len(results) == 1
    assert results[0]["content"] == "content target"


def test_access_stats_json_each(tmp_db: MemoryDB):
    """Verify that _update_access_stats works with the new json_each implementation."""
    mid1 = tmp_db.add("content 1")
    mid2 = tmp_db.add("content 2")

    # Initially access_count is 0
    m1 = tmp_db.get(mid1)
    m2 = tmp_db.get(mid2)
    assert m1 is not None
    assert m2 is not None
    assert m1["access_count"] == 0
    assert m2["access_count"] == 0

    # Search should trigger update
    tmp_db.search("content")

    m1 = tmp_db.get(mid1)
    m2 = tmp_db.get(mid2)
    assert m1 is not None
    assert m2 is not None
    assert m1["access_count"] == 1
    assert m2["access_count"] == 1


def test_missing_ids_json_each_direct_sql(tmp_db: MemoryDB):
    """Directly test the SQL for missing_ids path since vector setup is complex."""
    mid1 = tmp_db.add("id 1")
    mid2 = tmp_db.add("id 2")

    # Simulate the query used in missing_ids part of search()
    missing_ids = [mid1, mid2, "nonexistent"]
    rows = tmp_db._conn.execute(
        "SELECT * FROM memories WHERE id IN (SELECT value FROM json_each(?))",
        (json.dumps(missing_ids),),
    ).fetchall()

    assert len(rows) == 2
    ids = {row["id"] for row in rows}
    assert mid1 in ids
    assert mid2 in ids
