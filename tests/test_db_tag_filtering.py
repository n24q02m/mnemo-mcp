import json
from datetime import UTC, datetime

from mnemo_mcp.db import MemoryDB


def test_search_tags_pagination_bug(tmp_path):
    """
    Test that searching with tags finds items even if they are outside
    the initial limit of the base query (FTS or Vector).

    This simulates the case where we have many items matching the text query,
    but only a few (deep in the results) match the tag filter.
    """
    db_path = tmp_path / "test_db.sqlite"
    db = MemoryDB(db_path)

    # Insert 100 items matching "common"
    # Items 0-89 have no tags
    # Items 90-99 have tag "target"
    # If we search for "common" with limit=5, and the DB returns 0-89 first,
    # a naive post-filter would see 0-15 (limit*3), filter them out (no tags), and return empty.

    now = datetime.now(UTC).isoformat()
    params = []
    for i in range(100):
        mid = f"id_{i}"
        content = f"This is a common memory {i}"
        tags = ["target"] if i >= 90 else []
        params.append((mid, content, "general", json.dumps(tags), now, now, now))

    db._conn.executemany(
        """INSERT INTO memories (id, content, category, tags, created_at, updated_at, access_count, last_accessed)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
        params,
    )
    db._conn.commit()

    # Search for "common" with tag "target"
    # We expect to find the items 90-99
    # limit=5 means we want top 5 matches.
    results = db.search(query="common", tags=["target"], limit=5)

    # If the bug exists, this might be empty or less than 5
    assert len(results) > 0, (
        "Should find results even if they are deep in the FTS ranking"
    )
    assert len(results) == 5, f"Should find 5 results, found {len(results)}"

    for r in results:
        tags = json.loads(r["tags"])
        assert "target" in tags

    db.close()
