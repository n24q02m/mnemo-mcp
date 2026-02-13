from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from mnemo_mcp.server import lifespan


@pytest.fixture
def mock_server():
    """Mock FastMCP server instance."""
    return MagicMock(spec=FastMCP)


@pytest.fixture
def mock_settings():
    """Mock configuration settings."""
    with patch("mnemo_mcp.server.settings") as m:
        # Default mock values
        m.setup_api_keys.return_value = {}
        m.resolve_embedding_model.return_value = None
        m.resolve_embedding_dims.return_value = 0
        m.get_db_path.return_value = "memories.db"
        m.sync_enabled = False
        m.sync_remote = ""
        m.sync_folder = ""
        m.sync_interval = 0
        yield m


@pytest.fixture
def mock_db_class():
    """Mock MemoryDB class."""
    with patch("mnemo_mcp.server.MemoryDB") as m:
        db_instance = MagicMock()
        # Ensure stats returns a dict as expected by logging
        db_instance.stats.return_value = {"total_memories": 0, "vec_enabled": False}
        m.return_value = db_instance
        yield m


@pytest.fixture
def mock_sync():
    """Mock sync functions."""
    with (
        patch("mnemo_mcp.sync.start_auto_sync", create=True) as start,
        patch("mnemo_mcp.sync.stop_auto_sync", create=True) as stop,
    ):
        yield start, stop


@pytest.fixture
def mock_embedder():
    """Mock embedder availability check."""
    with patch("mnemo_mcp.embedder.check_embedding_available") as m:
        m.return_value = 0  # Default: not available
        yield m


@pytest.mark.asyncio
async def test_lifespan_no_keys_fts5_fallback(
    mock_server, mock_settings, mock_db_class, mock_sync
):
    """Test startup with no API keys (fallback to FTS5)."""
    # Setup
    mock_settings.setup_api_keys.return_value = {}

    # Run lifespan
    async with lifespan(mock_server) as ctx:
        # Verify context
        assert ctx["db"] is not None
        assert ctx["embedding_model"] is None
        assert ctx["embedding_dims"] == 0

        # Verify calls
        mock_settings.setup_api_keys.assert_called_once()
        mock_db_class.assert_called_once_with("memories.db", embedding_dims=0)

        # Verify sync not started
        start_sync, _ = mock_sync
        start_sync.assert_not_called()


@pytest.mark.asyncio
async def test_lifespan_explicit_model_valid(
    mock_server, mock_settings, mock_db_class, mock_sync, mock_embedder
):
    """Test startup with explicitly configured valid embedding model."""
    # Setup
    mock_settings.setup_api_keys.return_value = {"API_KEY": ["valid"]}
    mock_settings.resolve_embedding_model.return_value = "test-model"
    mock_embedder.return_value = 1536  # Native dims

    # Run lifespan
    async with lifespan(mock_server) as ctx:
        assert ctx["embedding_model"] == "test-model"
        # Should use default dims (768) if stored dims is 0
        assert ctx["embedding_dims"] == 768

        mock_embedder.assert_called_with("test-model")
        mock_db_class.assert_called_with("memories.db", embedding_dims=768)


@pytest.mark.asyncio
async def test_lifespan_explicit_model_invalid(
    mock_server, mock_settings, mock_db_class, mock_sync, mock_embedder
):
    """Test startup with explicitly configured but invalid embedding model."""
    # Setup
    mock_settings.setup_api_keys.return_value = {"API_KEY": ["valid"]}
    mock_settings.resolve_embedding_model.return_value = "bad-model"
    mock_embedder.return_value = 0  # Not available

    # Run lifespan
    async with lifespan(mock_server) as ctx:
        assert ctx["embedding_model"] is None

        mock_embedder.assert_called_with("bad-model")
        # Should fallback to 0 dims
        mock_db_class.assert_called_with("memories.db", embedding_dims=0)


@pytest.mark.asyncio
async def test_lifespan_auto_detect_model(
    mock_server, mock_settings, mock_db_class, mock_sync, mock_embedder
):
    """Test startup with auto-detection of embedding model."""
    # Setup
    mock_settings.setup_api_keys.return_value = {"API_KEY": ["valid"]}
    mock_settings.resolve_embedding_model.return_value = None

    # Make the second candidate succeed
    def check_side_effect(model):
        if model == "text-embedding-3-small":
            return 1536
        return 0

    mock_embedder.side_effect = check_side_effect

    # Run lifespan
    async with lifespan(mock_server) as ctx:
        assert ctx["embedding_model"] == "text-embedding-3-small"
        assert ctx["embedding_dims"] == 768

        # Verify DB initialized with correct dims
        mock_db_class.assert_called_with("memories.db", embedding_dims=768)


@pytest.mark.asyncio
async def test_lifespan_sync_enabled(
    mock_server, mock_settings, mock_db_class, mock_sync
):
    """Test startup with sync enabled."""
    # Setup
    mock_settings.sync_enabled = True
    start_sync, stop_sync = mock_sync

    # Run lifespan
    async with lifespan(mock_server) as ctx:
        # Verify sync started
        start_sync.assert_called_once_with(ctx["db"])

    # Verify sync stopped on exit
    stop_sync.assert_called_once()
    # Verify DB closed on exit
    ctx["db"].close.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_custom_dims(
    mock_server, mock_settings, mock_db_class, mock_sync, mock_embedder
):
    """Test startup with custom embedding dimensions."""
    # Setup
    mock_settings.setup_api_keys.return_value = {"API_KEY": ["valid"]}
    mock_settings.resolve_embedding_model.return_value = "test-model"
    mock_settings.resolve_embedding_dims.return_value = 512
    mock_embedder.return_value = 1024

    # Run lifespan
    async with lifespan(mock_server) as ctx:
        assert ctx["embedding_dims"] == 512
        mock_db_class.assert_called_with("memories.db", embedding_dims=512)
