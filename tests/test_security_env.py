import base64
import json
import os
from unittest.mock import patch

from mnemo_mcp.sync import _prepare_rclone_env


def test_environment_sanitization():
    """Verify that sensitive environment variables are filtered out and allowed ones are kept."""
    sensitive_var = "SUPER_SECRET_KEY"
    sensitive_value = "1234567890"

    # Setup environment with a mix of safe, sensitive, and rclone variables
    test_env = {
        sensitive_var: sensitive_value,
        "PATH": "/usr/bin:/bin",
        "RCLONE_CONFIG_MYREMOTE_TYPE": "drive",
        "RCLONE_CONFIG_MYREMOTE_TOKEN": base64.b64encode(
            json.dumps({"token": "abc"}).encode()
        ).decode(),
        "HOME": "/home/user",
        "UNKOWN_VAR": "should_be_removed",
    }

    with patch.dict(os.environ, test_env, clear=True):
        env = _prepare_rclone_env()

        # Verify sensitive variable is REMOVED
        assert sensitive_var not in env, "Sensitive variable leaked!"
        assert "UNKOWN_VAR" not in env, "Unknown variable leaked!"

        # Verify allowlisted variables are KEPT
        assert "PATH" in env
        assert env["PATH"] == "/usr/bin:/bin"
        assert "HOME" in env

        # Verify RCLONE variables are KEPT
        assert "RCLONE_CONFIG_MYREMOTE_TYPE" in env
        assert env["RCLONE_CONFIG_MYREMOTE_TYPE"] == "drive"

        # Verify token decoding logic still works
        assert "RCLONE_CONFIG_MYREMOTE_TOKEN" in env
        # Should be decoded JSON string
        assert env["RCLONE_CONFIG_MYREMOTE_TOKEN"] == '{"token": "abc"}'


def test_environment_allowlist_case_insensitivity():
    """Verify that allowlist matching handles case correctly (if applicable)."""
    # Assuming the implementation uppercases keys for checking against allowlist
    # but preserves original key in output.

    # Note: On Linux, env vars are case sensitive. On Windows, they are not.
    # The implementation uppercases the key from os.environ to check against _ENV_ALLOWLIST.

    with patch.dict(os.environ, {"path": "/usr/bin"}, clear=True):
        env = _prepare_rclone_env()
        # "path" (lowercase) matches "PATH" in allowlist because implementation does key.upper()
        assert "path" in env
        assert env["path"] == "/usr/bin"
