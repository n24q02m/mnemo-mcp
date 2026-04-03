"""Tests for relay_setup module."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

from mnemo_mcp.relay_setup import (
    CLOUD_KEYS,
    DEFAULT_RELAY_URL,
    apply_config,
    ensure_config,
    load_relay_config,
)


class TestConstants:
    """Test module constants."""

    def test_default_relay_url(self):
        assert DEFAULT_RELAY_URL == "https://mnemo-mcp.n24q02m.com"

    def test_cloud_keys(self):
        assert "JINA_AI_API_KEY" in CLOUD_KEYS
        assert "GEMINI_API_KEY" in CLOUD_KEYS
        assert "OPENAI_API_KEY" in CLOUD_KEYS
        assert "COHERE_API_KEY" in CLOUD_KEYS


class TestLoadRelayConfig:
    """Test load_relay_config function."""

    @patch("mcp_relay_core.storage.config_file.read_config")
    def test_returns_config_from_file(self, mock_read):
        mock_read.return_value = {"GEMINI_API_KEY": "AIza_test"}
        result = load_relay_config()
        assert result == {"GEMINI_API_KEY": "AIza_test"}
        mock_read.assert_called_once_with("mnemo-mcp")

    @patch("mcp_relay_core.storage.config_file.read_config")
    def test_returns_none_when_no_config(self, mock_read):
        mock_read.return_value = None
        result = load_relay_config()
        assert result is None

    @patch("mcp_relay_core.storage.config_file.read_config")
    def test_returns_none_when_no_cloud_keys(self, mock_read):
        mock_read.return_value = {"UNKNOWN_KEY": "value"}
        result = load_relay_config()
        assert result is None


class TestApplyConfig:
    """Test apply_config function."""

    def test_applies_new_keys(self, monkeypatch):
        """Sets environment variables for keys not already in env."""
        for key in CLOUD_KEYS:
            monkeypatch.delenv(key, raising=False)

        config = {
            "JINA_AI_API_KEY": "jina_test_key",
            "GEMINI_API_KEY": "AIza_test_key",
        }
        apply_config(config)

        assert os.environ.get("JINA_AI_API_KEY") == "jina_test_key"
        assert os.environ.get("GEMINI_API_KEY") == "AIza_test_key"

    def test_skips_existing_env_vars(self, monkeypatch):
        """Does not overwrite existing env vars."""
        monkeypatch.setenv("JINA_AI_API_KEY", "existing_key")

        config = {"JINA_AI_API_KEY": "new_key"}
        apply_config(config)

        assert os.environ.get("JINA_AI_API_KEY") == "existing_key"

    def test_skips_empty_values(self, monkeypatch):
        """Does not set empty string values."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        config = {"GEMINI_API_KEY": "", "OPENAI_API_KEY": "sk_test"}
        apply_config(config)

        assert os.environ.get("GEMINI_API_KEY") is None
        assert os.environ.get("OPENAI_API_KEY") == "sk_test"

    def test_multiple_keys_with_mixed_states(self, monkeypatch):
        """Handles a mix of new, existing, and empty values."""
        monkeypatch.setenv("COHERE_API_KEY", "existing")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("JINA_AI_API_KEY", raising=False)

        config = {
            "COHERE_API_KEY": "should_not_overwrite",
            "OPENAI_API_KEY": "new_openai",
            "JINA_AI_API_KEY": "",
        }
        apply_config(config)

        assert os.environ.get("COHERE_API_KEY") == "existing"
        assert os.environ.get("OPENAI_API_KEY") == "new_openai"
        assert os.environ.get("JINA_AI_API_KEY") is None


class TestEnsureConfig:
    """Test ensure_config async function."""

    @patch("mcp_relay_core.storage.config_file.read_config")
    async def test_returns_config_from_file(self, mock_read, monkeypatch):
        for key in CLOUD_KEYS:
            monkeypatch.delenv(key, raising=False)
        mock_read.return_value = {"GEMINI_API_KEY": "AIza_test"}
        result = await ensure_config()
        assert result == {"GEMINI_API_KEY": "AIza_test"}

    @patch("mcp_relay_core.relay.client.create_session", new_callable=AsyncMock)
    @patch("mcp_relay_core.storage.config_file.read_config")
    async def test_relay_setup_fails_gracefully(self, mock_read, mock_session):
        mock_read.return_value = None
        mock_session.side_effect = ConnectionError("Cannot reach server")
        result = await ensure_config()
        assert result is None

    @patch("mnemo_mcp.relay_setup.apply_config")
    @patch("mcp_relay_core.storage.config_file.write_config")
    @patch("mcp_relay_core.relay.client.poll_for_result", new_callable=AsyncMock)
    @patch("mcp_relay_core.relay.client.create_session", new_callable=AsyncMock)
    @patch("mcp_relay_core.storage.config_file.read_config")
    async def test_relay_setup_success(
        self, mock_read, mock_session, mock_poll, mock_write, mock_apply, monkeypatch
    ):
        for key in CLOUD_KEYS:
            monkeypatch.delenv(key, raising=False)
        mock_read.return_value = None
        mock_session.return_value = MagicMock(
            relay_url="https://mnemo-mcp.n24q02m.com/#k=abc&p=xyz",
            session_id="test-session",
        )
        config = {
            "JINA_AI_API_KEY": "jina_test",
            "GEMINI_API_KEY": "AIza_test",
        }
        mock_poll.return_value = config

        with (
            patch("httpx.AsyncClient") as mock_httpx,
            patch("mnemo_mcp.config.settings") as mock_settings,
        ):
            mock_client = AsyncMock()
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_settings.google_drive_client_id = ""

            result = await ensure_config()

        assert result == config
        mock_write.assert_called_once_with("mnemo-mcp", config)
        mock_apply.assert_called_once_with(config)

    @patch("mcp_relay_core.relay.client.poll_for_result", new_callable=AsyncMock)
    @patch("mcp_relay_core.relay.client.create_session", new_callable=AsyncMock)
    @patch("mcp_relay_core.storage.config_file.read_config")
    async def test_relay_setup_timeout(self, mock_read, mock_session, mock_poll):
        mock_read.return_value = None
        mock_session.return_value = MagicMock(relay_url="https://example.com")
        mock_poll.side_effect = RuntimeError("Timeout")
        result = await ensure_config()
        assert result is None
