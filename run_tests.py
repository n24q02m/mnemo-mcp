import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath("src"))

sys.modules['mcp_core'] = unittest.mock.MagicMock()
sys.modules['mcp_core.storage'] = unittest.mock.MagicMock()
sys.modules['mcp_core.storage.per_plugin_store'] = unittest.mock.MagicMock()
sys.modules['mcp_core.transport'] = unittest.mock.MagicMock()
sys.modules['mcp_core.transport.local_server'] = unittest.mock.MagicMock()
sys.modules['mcp_core.relay'] = unittest.mock.MagicMock()
sys.modules['mcp_core.relay.tool_helpers'] = unittest.mock.MagicMock()

# mock importlib.metadata.version
import importlib.metadata
importlib.metadata.version = lambda *args: "0.0.1"

import pytest
sys.exit(pytest.main(["-v", "tests/test_db.py"]))
