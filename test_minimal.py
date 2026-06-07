from unittest.mock import MagicMock, patch
import os
import shutil
from pathlib import Path
import sys

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

def test_removes_existing_cache(tmp_path):
    from mnemo_mcp.setup_tool import clear_model_cache
    model_dir = tmp_path / "models--org--model"
    model_dir.mkdir(parents=True)
    with patch.dict("os.environ", {"QWEN3_EMBED_CACHE_PATH": str(tmp_path)}):
        result = clear_model_cache("org/model")
    assert result == str(model_dir)
    assert not model_dir.exists()

def test_returns_none_when_cache_missing(tmp_path):
    from mnemo_mcp.setup_tool import clear_model_cache
    with patch.dict("os.environ", {"QWEN3_EMBED_CACHE_PATH": str(tmp_path)}):
        result = clear_model_cache("nonexistent/model")
    assert result is None
