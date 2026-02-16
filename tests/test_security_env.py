import os
from unittest.mock import patch

from mnemo_mcp.sync import _prepare_rclone_env


def test_sensitive_env_vars_filtered():
    """Ensure sensitive API keys are not passed to rclone."""
    with patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "sk-secret",
            "GEMINI_API_KEY": "AIza-secret",
            "RCLONE_CONFIG_MYREMOTE_TYPE": "drive",
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "AWS_ACCESS_KEY_ID": "AKIA...",
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json",
            "SSH_AUTH_SOCK": "/tmp/ssh-agent.sock",
        },
    ):
        env = _prepare_rclone_env()

        # These should be removed
        assert "OPENAI_API_KEY" not in env, "OPENAI_API_KEY should be filtered"
        assert "GEMINI_API_KEY" not in env, "GEMINI_API_KEY should be filtered"

        # These should remain
        assert "RCLONE_CONFIG_MYREMOTE_TYPE" in env
        assert "PATH" in env
        assert "HOME" in env
        assert "AWS_ACCESS_KEY_ID" in env
        assert "GOOGLE_APPLICATION_CREDENTIALS" in env
        assert "SSH_AUTH_SOCK" in env
