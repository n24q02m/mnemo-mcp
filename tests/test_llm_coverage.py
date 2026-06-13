from unittest.mock import patch

import pytest

from mnemo_mcp import llm


def test_detect_provider_from_model_string():
    assert llm.detect_provider("openai/gpt-4") == "openai"
    assert llm.detect_provider("Anthropic:claude-3") == "anthropic"
    assert llm.detect_provider("gemini/pro") == "gemini"
    assert llm.detect_provider("xai:grok") == "xai"
    assert llm.detect_provider("unknown/model") is None
    assert llm.detect_provider("openai") is None  # No separator


def test_get_default_model_edge_cases(monkeypatch):
    # Empty pairs and pairs without separators
    monkeypatch.setenv("LLM_MODELS", " , , openai , gemini=model1")
    assert llm.get_default_model("gemini") == "model1"

    # Pair without separator
    monkeypatch.setenv("LLM_MODELS", "openai,gemini=model2")
    assert llm.get_default_model("openai") == llm._DEFAULT_MODELS["openai"]
    assert llm.get_default_model("gemini") == "model2"

    # Empty model in pair
    monkeypatch.setenv("LLM_MODELS", "openai=,gemini=model3")
    assert llm.get_default_model("openai") == llm._DEFAULT_MODELS["openai"]
    assert llm.get_default_model("gemini") == "model3"


@pytest.mark.asyncio
async def test_call_llm_exception_log(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    # Force acompletion to fail to hit the exception handler
    with patch("mcp_core.llm.acompletion", side_effect=Exception("Simulated failure")):
        with patch.object(llm.logger, "warning") as mock_warn:
            result = await llm.call_llm("test", provider="openai")
            assert result is None
            assert mock_warn.called
            args, _ = mock_warn.call_args
            assert "failed: Simulated failure" in args[0]
