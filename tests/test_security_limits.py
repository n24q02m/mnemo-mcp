from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.server import memory


@pytest.mark.asyncio
async def test_search_limit_clamping():
    """Verify that search limit is clamped to prevent DoS."""
    mock_db = MagicMock()
    mock_db.search = MagicMock(return_value=[])

    with patch("mnemo_mcp.server._get_ctx") as mock_get_ctx:
        mock_get_ctx.return_value = (mock_db, None, 0)
        with patch("mnemo_mcp.server._embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            huge_limit = 1000000
            await memory(action="search", query="test", limit=huge_limit)
            args, kwargs = mock_db.search.call_args
            actual_limit = kwargs.get("limit")
            assert actual_limit == 100, f"Limit expected to be 100, got {actual_limit}"


@pytest.mark.asyncio
async def test_list_limit_clamping():
    """Verify that list limit is clamped to prevent DoS."""
    mock_db = MagicMock()
    mock_db.list_memories = MagicMock(return_value=[])

    with patch("mnemo_mcp.server._get_ctx") as mock_get_ctx:
        mock_get_ctx.return_value = (mock_db, None, 0)
        huge_limit = 1000000
        await memory(action="list", limit=huge_limit)
        args, kwargs = mock_db.list_memories.call_args
        actual_limit = kwargs.get("limit")
        assert actual_limit == 100, f"Limit expected to be 100, got {actual_limit}"


@pytest.mark.asyncio
async def test_archived_limit_enforced_in_db():
    """Verify that the db method actually receives the clamped limit."""
    from pathlib import Path

    from mnemo_mcp.db import MemoryDB

    # Create an in-memory db
    db = MemoryDB(Path(":memory:"), embedding_dims=0)

    for i in range(105):
        db._conn.execute(
            "INSERT INTO archived_memories (id, content, category, tags, importance, archived_at, created_at, updated_at, access_count, last_accessed, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"old_{i}",
                "x",
                "test",
                "[]",
                0.1,
                "2000-01-01",
                "2000-01-01",
                "2000-01-01",
                1,
                "2000-01-01",
                None,
            ),
        )
    db._conn.commit()

    results = db.list_archived(limit=1000)
    assert len(results) == 100, f"Expected clamped 100, got {len(results)}"
