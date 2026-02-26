from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.server import memory


@pytest.mark.asyncio
async def test_search_limit_clamping():
    """Verify that search limit is clamped to prevent DoS."""
    # Mock context and database
    mock_db = MagicMock()
    mock_db.search = MagicMock(return_value=[])

    # Mock _get_ctx to return our mock db
    with patch("mnemo_mcp.server._get_ctx") as mock_get_ctx:
        mock_get_ctx.return_value = (mock_db, None, 0)

        # Mock _embed to avoid actual embedding
        with patch("mnemo_mcp.server._embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            # Call memory with a huge limit
            huge_limit = 1000000
            await memory(action="search", query="test", limit=huge_limit)

            # Check what limit was passed to db.search
            args, kwargs = mock_db.search.call_args
            actual_limit = kwargs.get("limit")

            # The limit should be clamped to 100
            assert actual_limit == 100, f"Limit expected to be 100, got {actual_limit}"


@pytest.mark.asyncio
async def test_list_limit_clamping():
    """Verify that list limit is clamped to prevent DoS."""
    # Mock context and database
    mock_db = MagicMock()
    mock_db.list_memories = MagicMock(return_value=[])

    # Mock _get_ctx to return our mock db
    with patch("mnemo_mcp.server._get_ctx") as mock_get_ctx:
        mock_get_ctx.return_value = (mock_db, None, 0)

        # Call memory with a huge limit
        huge_limit = 1000000
        await memory(action="list", limit=huge_limit)

        # Check what limit was passed to db.list_memories
        args, kwargs = mock_db.list_memories.call_args
        actual_limit = kwargs.get("limit")

        # The limit should be clamped to 100
        assert actual_limit == 100, f"Limit expected to be 100, got {actual_limit}"
