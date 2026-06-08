import os
from unittest.mock import patch

from mnemo_mcp.setup_tool import clear_model_cache


def test_clear_model_cache_exists(tmp_path):
    # Setup: Create a mock cache directory
    cache_dir = tmp_path / "qwen3_embed_cache"
    cache_dir.mkdir()
    model_name = "org/model"
    safe_name = model_name.replace("/", "--")
    model_cache = cache_dir / f"models--{safe_name}"
    model_cache.mkdir()
    (model_cache / "some_file").write_text("data")

    with patch.dict(os.environ, {"QWEN3_EMBED_CACHE_PATH": str(cache_dir)}):
        result = clear_model_cache(model_name)

        assert result == str(model_cache)
        assert not model_cache.exists()


def test_clear_model_cache_not_exists(tmp_path):
    cache_dir = tmp_path / "qwen3_embed_cache"
    cache_dir.mkdir()
    model_name = "other/model"

    with patch.dict(os.environ, {"QWEN3_EMBED_CACHE_PATH": str(cache_dir)}):
        result = clear_model_cache(model_name)

        assert result is None


def test_clear_model_cache_default_path(tmp_path, monkeypatch):
    # Mock tempfile.gettempdir to use our tmp_path
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    # The function uses os.path.join(tempfile.gettempdir(), "qwen3_embed_cache")
    cache_dir = tmp_path / "qwen3_embed_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_name = "default/model"
    safe_name = model_name.replace("/", "--")
    model_cache = cache_dir / f"models--{safe_name}"
    model_cache.mkdir()

    # Ensure env var is NOT set
    if "QWEN3_EMBED_CACHE_PATH" in os.environ:
        monkeypatch.delenv("QWEN3_EMBED_CACHE_PATH")

    result = clear_model_cache(model_name)

    assert result == str(model_cache)
    assert not model_cache.exists()
