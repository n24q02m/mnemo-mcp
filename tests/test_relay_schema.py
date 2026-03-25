"""Tests for relay_schema module."""

from mnemo_mcp.relay_schema import RELAY_SCHEMA


class TestRelaySchema:
    """Test relay config schema definition."""

    def test_schema_has_server_name(self):
        assert RELAY_SCHEMA["server"] == "mnemo-mcp"

    def test_schema_has_display_name(self):
        assert RELAY_SCHEMA["displayName"] == "Mnemo MCP"

    def test_schema_has_two_modes(self):
        modes = RELAY_SCHEMA["modes"]
        assert len(modes) == 2

    def test_local_mode(self):
        local = RELAY_SCHEMA["modes"][0]
        assert local["id"] == "local"
        assert local["fields"] == []

    def test_proxy_mode(self):
        proxy = RELAY_SCHEMA["modes"][1]
        assert proxy["id"] == "proxy"
        assert len(proxy["fields"]) == 2

    def test_proxy_mode_url_field(self):
        url_field = RELAY_SCHEMA["modes"][1]["fields"][0]
        assert url_field["key"] == "LITELLM_PROXY_URL"
        assert url_field["type"] == "url"

    def test_proxy_mode_key_field(self):
        key_field = RELAY_SCHEMA["modes"][1]["fields"][1]
        assert key_field["key"] == "LITELLM_PROXY_KEY"
        assert key_field["type"] == "password"
        assert key_field.get("required") is False
