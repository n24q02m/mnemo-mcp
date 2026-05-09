import sys
from unittest.mock import MagicMock, patch

# Mock mcp_core
sys.modules['mcp_core'] = MagicMock()
sys.modules['mcp_core.relay'] = MagicMock()
sys.modules['mcp_core.relay.tool_helpers'] = MagicMock()

with patch("importlib.metadata.version", return_value="0.1.0"):
    import pytest
    if __name__ == "__main__":
        sys.exit(pytest.main(["tests/test_db.py", "tests/test_server.py", "-v"]))
