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

    def test_cloud_mode(self):
        cloud = RELAY_SCHEMA["modes"][1]
        assert cloud["id"] == "cloud"
        assert len(cloud["fields"]) == 1

    def test_cloud_mode_api_keys_field(self):
        api_keys_field = RELAY_SCHEMA["modes"][1]["fields"][0]
        assert api_keys_field["key"] == "API_KEYS"
        assert api_keys_field["type"] == "password"
