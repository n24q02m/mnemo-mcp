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

# Setup mocks for dependencies in sys.modules
sys.modules["mnemo_mcp.db"] = MagicMock()
sys.modules["mnemo_mcp.embedder"] = MagicMock()

# Mock FastMCP
mock_mcp_module = MagicMock()
mock_fast_mcp = MagicMock()

def identity_decorator(*args, **kwargs):
    def wrapper(func):
        return func
    return wrapper

mock_fast_mcp.tool.side_effect = identity_decorator
mock_fast_mcp.resource.side_effect = identity_decorator
mock_fast_mcp.prompt.side_effect = identity_decorator

mock_mcp_module.FastMCP.return_value = mock_fast_mcp
sys.modules["mcp.server.fastmcp"] = mock_mcp_module

# Import the module under test (must be after patching)
from mnemo_mcp import server  # noqa: E402


@pytest.mark.asyncio
async def test_log_level_invalid_rejection():
    """Verify that setting an invalid log level is rejected and does not crash."""
    with patch("mnemo_mcp.server.logger") as mock_logger:
        with patch("mnemo_mcp.server.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            with patch("mnemo_mcp.server._get_ctx", return_value=(MagicMock(), MagicMock(), MagicMock())):
                # Action
                result = await server.config(action="set", key="log_level", value="INVALID_LEVEL")

                # Assertions
                assert '"error":' in result
                assert "Invalid log level" in result

                # Verify logger was NOT touched
                mock_logger.remove.assert_not_called()
                mock_logger.add.assert_not_called()


@pytest.mark.asyncio
async def test_log_level_valid_update():
    """Verify that setting a valid log level updates the logger."""
    with patch("mnemo_mcp.server.logger") as mock_logger:
        with patch("mnemo_mcp.server.settings") as mock_settings:
            mock_settings.log_level = "INFO"
            with patch("mnemo_mcp.server._get_ctx", return_value=(MagicMock(), MagicMock(), MagicMock())):
                # Action
                result = await server.config(action="set", key="log_level", value="DEBUG")

                # Assertions
                assert '"status": "updated"' in result

                # Verify logger was reconfigured
                mock_logger.remove.assert_called_once()
                mock_logger.add.assert_called_once()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(test_log_level_invalid_rejection())
        asyncio.run(test_log_level_valid_update())
        print("All tests passed.")
    except Exception as e:
        print(f"Test FAILED: {e}")
        sys.exit(1)
