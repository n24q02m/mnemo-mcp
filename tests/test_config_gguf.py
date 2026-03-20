"""Test missing ImportError coverage for _has_gguf_support."""

import sys
from unittest.mock import patch

from mnemo_mcp.config import _has_gguf_support


def test_gguf_support_import_error():
    import builtins

    orig_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "llama_cpp":
            raise ImportError("mocked")
        return orig_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with patch.dict(sys.modules):
            if "llama_cpp" in sys.modules:
                del sys.modules["llama_cpp"]
            assert _has_gguf_support() is False
