import os
from contextvars import copy_context
from unittest.mock import patch

from mnemo_mcp.credential_state import (
    api_key_for_model,
    credentials_for_current_request,
    get_current_sub,
    set_current_sub,
)


def test_current_sub_defaults_to_none():
    """Verify that the current sub defaults to None."""
    assert get_current_sub() is None


def test_set_current_sub():
    """Verify that set_current_sub updates the contextvar."""
    set_current_sub("user_123")
    assert get_current_sub() == "user_123"
    set_current_sub(None)
    assert get_current_sub() is None


def test_current_sub_isolation():
    """Verify that contextvars isolation works as expected."""

    def run_in_context():
        set_current_sub("context_user")
        assert get_current_sub() == "context_user"

    # Before running in context
    assert get_current_sub() is None

    ctx = copy_context()
    ctx.run(run_in_context)

    # After running in context (should still be None in the main context)
    assert get_current_sub() is None


def test_get_current_sub_with_empty_string():
    """Verify that get_current_sub returns None for empty string."""
    set_current_sub("")
    assert get_current_sub() is None
    set_current_sub(None)  # Reset


def test_credentials_for_current_request_none():
    """Verify credentials_for_current_request when sub is None."""
    set_current_sub(None)
    # It filters os.environ by CLOUD_KEYS
    with patch.dict(
        os.environ, {"JINA_AI_API_KEY": "test-key", "OTHER_VAR": "secret"}, clear=True
    ):
        creds = credentials_for_current_request()
        assert "JINA_AI_API_KEY" in creds
        assert creds["JINA_AI_API_KEY"] == "test-key"
        assert "OTHER_VAR" not in creds


def test_credentials_for_current_request_with_sub():
    """Verify credentials_for_current_request when sub is set."""
    set_current_sub("user1")
    with patch("mcp_core.storage.per_plugin_store.PerPluginStore.load") as mock_load:
        mock_load.return_value = {"KEY": "VAL"}
        creds = credentials_for_current_request()
        assert creds == {"KEY": "VAL"}
    set_current_sub(None)


def test_api_key_for_model_none():
    """Verify api_key_for_model when sub is None."""
    set_current_sub(None)
    assert api_key_for_model("gpt-4") is None


def test_api_key_for_model_with_sub():
    """Verify api_key_for_model when sub is set."""
    set_current_sub("user1")
    with (
        patch(
            "mcp_core.llm.providers.key_env_for_model", return_value="GEMINI_API_KEY"
        ),
        patch(
            "mnemo_mcp.credential_state.credentials_for_current_request",
            return_value={"GEMINI_API_KEY": "secret-gemini"},
        ),
    ):
        assert api_key_for_model("gemini-pro") == "secret-gemini"
    set_current_sub(None)
