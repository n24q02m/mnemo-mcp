import importlib.metadata
import sys
from unittest.mock import MagicMock, patch

import pytest


# Apply patch to importlib.metadata.version globally for this module
# Must happen before other imports if they use version checking
def mock_version(name):
    if name == "mnemo-mcp":
        return "0.0.0-test"
    raise importlib.metadata.PackageNotFoundError(name)


patcher = patch("importlib.metadata.version", side_effect=mock_version)
patcher.start()


@pytest.fixture
def mock_dependencies():
    """Mock heavy dependencies in sys.modules to avoid importing them."""
    mock_db = MagicMock()
    mock_embedder = MagicMock()
    mock_fast_mcp = MagicMock()

    # Setup FastMCP mock to be transparent
    def identity_decorator(*args, **kwargs):
        def wrapper(func):
            return func

        return wrapper

    mock_fast_mcp.tool.side_effect = identity_decorator
    mock_fast_mcp.resource.side_effect = identity_decorator
    mock_fast_mcp.prompt.side_effect = identity_decorator

    mock_mcp_module = MagicMock()
    mock_mcp_module.FastMCP.return_value = mock_fast_mcp

    modules_to_patch = {
        "mnemo_mcp.db": mock_db,
        "mnemo_mcp.embedder": mock_embedder,
        "mcp.server.fastmcp": mock_mcp_module,
    }

    # Use patch.dict to safely modify sys.modules and RESTORE it afterwards
    with patch.dict(sys.modules, modules_to_patch):
        # Ensure mnemo_mcp.server is unloaded so it can be re-imported with mocks
        if "mnemo_mcp.server" in sys.modules:
            del sys.modules["mnemo_mcp.server"]
        yield
        # Cleanup: Remove mnemo_mcp.server so subsequent tests re-import the real one
        if "mnemo_mcp.server" in sys.modules:
            del sys.modules["mnemo_mcp.server"]


@pytest.mark.asyncio
async def test_log_level_invalid_rejection(mock_dependencies):
    """Verify that setting an invalid log level is rejected and does not crash."""
    from mnemo_mcp import server

    # Use patch.object to patch the exact object on the imported module
    with patch.object(server, "logger") as mock_logger:
        with patch.object(server, "settings") as mock_settings:
            mock_settings.log_level = "INFO"
            with patch.object(
                server, "_get_ctx", return_value=(MagicMock(), MagicMock(), MagicMock())
            ):
                # Action
                result = await server.config(
                    action="set", key="log_level", value="INVALID_LEVEL"
                )

                # Assertions
                assert '"error":' in result
                assert "Invalid log level" in result

                # Verify logger was NOT touched
                mock_logger.remove.assert_not_called()
                mock_logger.add.assert_not_called()


@pytest.mark.asyncio
async def test_log_level_valid_update(mock_dependencies):
    """Verify that setting a valid log level updates the logger."""
    from mnemo_mcp import server

    with patch.object(server, "logger") as mock_logger:
        with patch.object(server, "settings") as mock_settings:
            mock_settings.log_level = "INFO"
            with patch.object(
                server, "_get_ctx", return_value=(MagicMock(), MagicMock(), MagicMock())
            ):
                # Action
                result = await server.config(
                    action="set", key="log_level", value="DEBUG"
                )

                # Assertions
                assert '"status": "updated"' in result

                # Verify logger was reconfigured
                mock_logger.remove.assert_called_once()
                mock_logger.add.assert_called_once()
