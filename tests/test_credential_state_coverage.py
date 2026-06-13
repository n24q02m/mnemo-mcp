import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from mnemo_mcp.credential_state import (
    CLOUD_KEYS,
    _sub_data_dir,
    credentials_for_current_request,
    get_current_sub,
    set_current_sub,
    store_for_sub,
)


class TestCredentialStateCoverage:
    def test_get_set_current_sub(self):
        """Test set_current_sub and get_current_sub."""
        set_current_sub("test_sub")
        assert get_current_sub() == "test_sub"
        set_current_sub(None)
        assert get_current_sub() is None

    def test_credentials_for_current_request_sub_none(self, monkeypatch):
        """Test credentials_for_current_request when sub is None (stdio/single-user)."""
        set_current_sub(None)

        # Set some cloud keys and some unrelated env vars
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
        monkeypatch.setenv("OTHER_VAR", "unrelated")

        creds = credentials_for_current_request()

        assert "OPENAI_API_KEY" in creds
        assert "ANTHROPIC_API_KEY" in creds
        assert creds["OPENAI_API_KEY"] == "sk-test"
        assert creds["ANTHROPIC_API_KEY"] == "ant-test"
        assert "OTHER_VAR" not in creds
        # Ensure only keys in CLOUD_KEYS are returned
        for k in creds:
            assert k in CLOUD_KEYS

    def test_credentials_for_current_request_sub_set_config_exists(
        self, tmp_path, monkeypatch
    ):
        """Test credentials_for_current_request when sub is set and config.json exists."""
        sub = "user_123"
        set_current_sub(sub)

        monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))

        # Prepare the config file
        config_data = {"GEMINI_API_KEY": "gemini-test", "CUSTOM_KEY": "val"}
        store_for_sub(sub, config_data)

        creds = credentials_for_current_request()

        assert creds == config_data
        set_current_sub(None)

    def test_credentials_for_current_request_sub_set_config_missing(
        self, tmp_path, monkeypatch
    ):
        """Test credentials_for_current_request when sub is set but config.json is missing."""
        sub = "user_456"
        set_current_sub(sub)

        monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))

        # Ensure directory exists but config.json does not
        _sub_data_dir(sub)

        creds = credentials_for_current_request()

        assert creds == {}
        set_current_sub(None)

    def test_sub_data_dir_logic(self, tmp_path, monkeypatch):
        """Verify _sub_data_dir hashing and path construction."""
        sub = "test_user"
        monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))

        path = _sub_data_dir(sub)

        expected_hash = hashlib.sha256(sub.encode("utf-8")).hexdigest()
        assert path == tmp_path / "subs" / expected_hash
        assert path.exists()
        assert path.is_dir()

    def test_sub_data_dir_default_base(self, monkeypatch):
        """Verify _sub_data_dir uses home dir fallback when MNEMO_DATA_DIR is missing."""
        monkeypatch.delenv("MNEMO_DATA_DIR", raising=False)
        sub = "another_user"

        # Mock Path.home() to return a controlled path
        fake_home = Path("/tmp/fake_home_for_coverage")
        with patch("pathlib.Path.home", return_value=fake_home):
            # Also mock mkdir to avoid actual directory creation
            with patch("pathlib.Path.mkdir"):
                path = _sub_data_dir(sub)

                expected_hash = hashlib.sha256(sub.encode("utf-8")).hexdigest()
                assert path == fake_home / ".mnemo-mcp" / "subs" / expected_hash

    def test_store_for_sub_permissions(self, tmp_path, monkeypatch):
        """Verify store_for_sub creates file with correct content and permissions."""
        sub = "perm_user"
        monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))
        config = {"KEY": "VALUE"}

        store_for_sub(sub, config)

        path = _sub_data_dir(sub) / "config.json"
        assert path.exists()
        assert json.loads(path.read_text()) == config

        if os.name != "nt":
            # Check for 0600 permissions
            assert (path.stat().st_mode & 0o777) == 0o600

    def test_store_for_sub_fchmod_error_handled(self, tmp_path, monkeypatch):
        """Verify store_for_sub handles fchmod OSError gracefully."""
        sub = "fchmod_user"
        monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))

        with patch("os.fchmod", side_effect=OSError("permission denied")):
            # Should not raise
            store_for_sub(sub, {"a": "b"})

        path = _sub_data_dir(sub) / "config.json"
        assert path.exists()
