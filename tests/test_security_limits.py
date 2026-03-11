from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.server import _handle_search, memory


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
async def test_handle_search_limit_clamped():
    """Verify that _handle_search limit is clamped independently."""
    mock_db = MagicMock()
    mock_db.search = MagicMock(return_value=[])

    with patch("mnemo_mcp.server._embed", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1, 0.2]
        await _handle_search(
            db=mock_db,
            query="test",
            category=None,
            tags=None,
            limit=1000,
            embedding_model="test_model",
            embedding_dims=2,
        )

        # Verify db.search was called with limit=100
        mock_db.search.assert_called_once_with(
            query="test", embedding=[0.1, 0.2], category=None, tags=None, limit=100
        )


@pytest.mark.asyncio
async def test_handle_search_limit_clamped_negative():
    """Verify that _handle_search limit is clamped independently for negative values."""
    mock_db = MagicMock()
    mock_db.search = MagicMock(return_value=[])

    with patch("mnemo_mcp.server._embed", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1, 0.2]
        await _handle_search(
            db=mock_db,
            query="test",
            category=None,
            tags=None,
            limit=-10,
            embedding_model="test_model",
            embedding_dims=2,
        )

        # Verify db.search was called with limit=1 (max 1)
        mock_db.search.assert_called_once_with(
            query="test", embedding=[0.1, 0.2], category=None, tags=None, limit=1
        )
