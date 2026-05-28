from unittest.mock import patch

import tiktoken

from mnemo_mcp import compression

# Use the mock already established in conftest.py
mock_encoding = tiktoken.get_encoding("cl100k_base")

def test_resolve_provider_priority(monkeypatch):
    # 1. Explicit wins
    monkeypatch.setenv("COMPRESSION_PROVIDER", "env-provider")
    with patch("mnemo_mcp.compression.detect_provider", return_value="auto-provider"):
        assert compression._resolve_provider("explicit-provider") == "explicit-provider"

    # 2. Env wins over auto-detect
    assert compression._resolve_provider(None) == "env-provider"

    # 3. Auto-detect is fallback
    monkeypatch.delenv("COMPRESSION_PROVIDER")
    with patch("mnemo_mcp.compression.detect_provider", return_value="auto-provider") as mock_detect:
        assert compression._resolve_provider(None) == "auto-provider"
        mock_detect.assert_called_once()

def test_resolve_model_priority(monkeypatch):
    # 1. Explicit wins
    monkeypatch.setenv("COMPRESSION_MODEL", "env-model")
    with patch("mnemo_mcp.compression.get_default_model", return_value="default-model"):
        assert compression._resolve_model("p", "explicit-model") == "explicit-model"

    # 2. Env wins over default
    assert compression._resolve_model("p", None) == "env-model"

    # 3. Default is fallback
    monkeypatch.delenv("COMPRESSION_MODEL")
    with patch("mnemo_mcp.compression.get_default_model", return_value="default-model") as mock_get_default:
        assert compression._resolve_model("p", None) == "default-model"
        mock_get_default.assert_called_once_with("p")

def test_env_compression_enabled(monkeypatch):
    # Default is True
    monkeypatch.delenv("COMPRESSION_ENABLED", raising=False)
    assert compression._env_compression_enabled() is True

    # Explicit values
    monkeypatch.setenv("COMPRESSION_ENABLED", "false")
    assert compression._env_compression_enabled() is False
    monkeypatch.setenv("COMPRESSION_ENABLED", "0")
    assert compression._env_compression_enabled() is False
    monkeypatch.setenv("COMPRESSION_ENABLED", "no")
    assert compression._env_compression_enabled() is False
    monkeypatch.setenv("COMPRESSION_ENABLED", "off")
    assert compression._env_compression_enabled() is False

    monkeypatch.setenv("COMPRESSION_ENABLED", "true")
    assert compression._env_compression_enabled() is True
    monkeypatch.setenv("COMPRESSION_ENABLED", "1")
    assert compression._env_compression_enabled() is True
    monkeypatch.setenv("COMPRESSION_ENABLED", "yes")
    assert compression._env_compression_enabled() is True
    monkeypatch.setenv("COMPRESSION_ENABLED", "on")
    assert compression._env_compression_enabled() is True

def test_count_tokens_uses_mocked_encoding():
    # count_tokens calls _ENCODING.encode(text)
    # The mock in conftest.py returns [0] * len(text)
    assert compression.count_tokens("abc") == 3
    assert compression.count_tokens("") == 0
