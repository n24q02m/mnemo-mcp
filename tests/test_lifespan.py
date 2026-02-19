"""Tests for server lifespan management."""

from unittest.mock import MagicMock, patch

import pytest

from mnemo_mcp.server import lifespan


@pytest.fixture
def mock_settings():
    with patch("mnemo_mcp.server.settings") as m:
        # Default happy path settings
        m.setup_api_keys.return_value = {"KEY": "123"}
        m.resolve_embedding_model.return_value = "test-model"
        m.resolve_embedding_dims.return_value = 0
        m.resolve_embedding_backend.return_value = "litellm"
        m.sync_enabled = False
        m.get_db_path.return_value = "test.db"
        m.resolve_local_embedding_model.return_value = "local-model"
        yield m


@pytest.fixture
def mock_db():
    with patch("mnemo_mcp.server.MemoryDB") as m:
        db_instance = MagicMock()
        db_instance.stats.return_value = {"total_memories": 10, "vec_enabled": True}
        db_instance.vec_enabled = True
        m.return_value = db_instance
        yield m


@pytest.fixture
def mock_embedder():
    with patch("mnemo_mcp.embedder.init_backend") as m:
        backend = MagicMock()
        backend.check_available.return_value = 100
        m.return_value = backend
        yield m


@pytest.fixture
def mock_sync():
    with (
        patch("mnemo_mcp.sync.start_auto_sync") as start,
        patch("mnemo_mcp.sync.stop_auto_sync") as stop,
    ):
        yield start, stop


@pytest.mark.asyncio
async def test_lifespan_happy_path_cloud(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test normal startup with cloud embedding."""
    mock_settings.resolve_embedding_backend.return_value = "litellm"
    mock_settings.resolve_embedding_model.return_value = "cloud-model"
    mock_settings.resolve_embedding_dims.return_value = 128

    # Setup backend mock
    backend = mock_embedder.return_value
    backend.check_available.return_value = 128

    server = MagicMock()
    async with lifespan(server) as ctx:
        assert ctx["embedding_model"] == "cloud-model"
        assert ctx["embedding_dims"] == 128
        assert ctx["db"] == mock_db.return_value

    # Verify cleanup
    mock_db.return_value.close.assert_called_once()
    mock_sync[1].assert_called_once()  # stop_auto_sync


@pytest.mark.asyncio
async def test_lifespan_auto_detect_success(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test auto-detection of embedding model."""
    mock_settings.resolve_embedding_backend.return_value = "litellm"
    mock_settings.resolve_embedding_model.return_value = None  # Trigger auto-detect
    mock_settings.resolve_embedding_dims.return_value = 0  # Ensure we get default

    # Mock init_backend to fail first candidate, succeed second
    backend1 = MagicMock()
    backend1.check_available.side_effect = Exception("Nope")

    backend2 = MagicMock()
    backend2.check_available.return_value = 768

    # First call fails, second succeeds
    mock_embedder.side_effect = [backend1, backend2, Exception("Should not reach")]

    server = MagicMock()
    async with lifespan(server) as ctx:
        # Should pick second candidate from _EMBEDDING_CANDIDATES
        # "gemini/gemini-embedding-001" is first, "text-embedding-3-small" is second
        assert ctx["embedding_model"] == "text-embedding-3-small"
        assert ctx["embedding_dims"] == 768


@pytest.mark.asyncio
async def test_lifespan_fallback_to_local(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test fallback to local embedding when cloud fails."""
    mock_settings.resolve_embedding_backend.return_value = "litellm"
    mock_settings.resolve_embedding_model.return_value = "bad-model"
    mock_settings.resolve_embedding_dims.return_value = 0

    # Fail cloud init (check_available returns 0)
    backend_cloud = MagicMock()
    backend_cloud.check_available.return_value = 0

    # Succeed local init
    backend_local = MagicMock()
    backend_local.check_available.return_value = 384

    mock_embedder.side_effect = [backend_cloud, backend_local]
    mock_settings.resolve_local_embedding_model.return_value = "all-MiniLM-L6-v2"

    server = MagicMock()
    async with lifespan(server) as ctx:
        assert ctx["embedding_model"] == "__local__"
        # Since resolve_embedding_dims returns 0, and we set local backend,
        # it executes: if embedding_dims == 0: embedding_dims = _DEFAULT_EMBEDDING_DIMS
        assert ctx["embedding_dims"] == 768


@pytest.mark.asyncio
async def test_lifespan_sync_enabled(mock_settings, mock_db, mock_embedder, mock_sync):
    """Test auto-sync startup."""
    mock_settings.sync_enabled = True
    mock_settings.sync_remote = "remote"
    mock_settings.sync_folder = "folder"
    mock_settings.sync_interval = 60

    start_sync, stop_sync = mock_sync

    server = MagicMock()
    async with lifespan(server):
        pass

    start_sync.assert_called_once_with(mock_db.return_value)
    stop_sync.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_local_backend_explicit(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test explicit local backend configuration."""
    mock_settings.resolve_embedding_backend.return_value = "local"
    mock_settings.resolve_local_embedding_model.return_value = "local-model"
    mock_settings.resolve_embedding_dims.return_value = 0

    backend = mock_embedder.return_value
    backend.check_available.return_value = 384

    server = MagicMock()
    async with lifespan(server) as ctx:
        assert ctx["embedding_model"] == "__local__"
        assert ctx["embedding_dims"] == 768  # Default for stored


@pytest.mark.asyncio
async def test_lifespan_api_keys_logging(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test API keys are logged."""
    mock_settings.setup_api_keys.return_value = {"A": 1, "B": 2}

    # We patch logger where it is used in server.py
    with patch("mnemo_mcp.server.logger") as mock_logger:
        server = MagicMock()
        async with lifespan(server):
            pass

        # Check that logger.info was called with key names
        found = False
        for call in mock_logger.info.call_args_list:
            arg = str(call)
            if "API keys configured" in arg and "A" in arg and "B" in arg:
                found = True
                break
        assert found, f"Logger calls: {mock_logger.info.call_args_list}"


@pytest.mark.asyncio
async def test_lifespan_explicit_cloud_exception_fallback(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test fallback when explicit cloud model initialization raises exception."""
    mock_settings.resolve_embedding_backend.return_value = "litellm"
    mock_settings.resolve_embedding_model.return_value = "crash-model"
    mock_settings.resolve_embedding_dims.return_value = 0

    # First call (cloud) raises Exception
    # Second call (local) succeeds
    backend_local = MagicMock()
    backend_local.check_available.return_value = 384

    mock_embedder.side_effect = [Exception("API Error"), backend_local]

    server = MagicMock()
    async with lifespan(server) as ctx:
        assert ctx["embedding_model"] == "__local__"
        assert ctx["embedding_dims"] == 768


@pytest.mark.asyncio
async def test_lifespan_all_backends_fail(
    mock_settings, mock_db, mock_embedder, mock_sync
):
    """Test behavior when both cloud and local backends fail."""
    mock_settings.resolve_embedding_backend.return_value = "litellm"
    mock_settings.resolve_embedding_model.return_value = "crash-model"

    # Cloud raises, Local raises
    mock_embedder.side_effect = [Exception("Cloud fail"), Exception("Local fail")]

    server = MagicMock()
    async with lifespan(server) as ctx:
        assert ctx["embedding_model"] is None
        assert (
            ctx["embedding_dims"] == 0
        )  # Or whatever resolve_embedding_dims returns (0)

    # Should still init DB
    mock_db.return_value.stats.assert_called()
