import sys
from unittest.mock import MagicMock, patch

# Mock dependencies that are missing in the environment
sys.modules['mcp_core'] = MagicMock()
sys.modules['mcp_core.relay.tool_helpers'] = MagicMock()
sys.modules['qwen3_embed'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()
mcp = MagicMock()
sys.modules['mcp'] = mcp
sys.modules['mcp.server'] = mcp.server
sys.modules['mcp.server.fastmcp'] = mcp.server.fastmcp
sys.modules['mcp.types'] = mcp.types
sys.modules['sqlite_vec'] = MagicMock()

import pytest

if __name__ == "__main__":
    sys.path.insert(0, "src")
    with patch("importlib.metadata.version", return_value="1.26.0"):
        sys.exit(pytest.main(["tests/test_reranker.py"]))
