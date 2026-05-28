import pytest
import os
from mnemo_mcp.reranker import _detect_rerank_provider

@pytest.mark.parametrize("model, expected", [
    ("jina_ai/jina-reranker-v3", "jina"),
    ("jina-reranker-v3", "jina"),
    ("JINA-RERANKER-V3", "jina"),
    ("jina_ai/custom", "jina"),
    ("rerank-v4.0-pro", "cohere"),
    ("cohere/rerank-v4.0-pro", "cohere"),
    ("RERANK-V4.0-PRO", "cohere"),
    ("cohere/custom", "cohere"),
])
def test_detect_rerank_provider_explicit(model, expected):
    """Test explicit provider prefixes."""
    assert _detect_rerank_provider(model) == expected

def test_detect_rerank_provider_fallback_jina(monkeypatch):
    """Test fallback to Jina when unknown model and JINA_AI_API_KEY is set."""
    monkeypatch.setenv("JINA_AI_API_KEY", "test-key")
    assert _detect_rerank_provider("unknown-model") == "jina"

def test_detect_rerank_provider_fallback_cohere(monkeypatch):
    """Test fallback to Cohere when unknown model and JINA_AI_API_KEY is not set."""
    monkeypatch.delenv("JINA_AI_API_KEY", raising=False)
    assert _detect_rerank_provider("unknown-model") == "cohere"

def test_detect_rerank_provider_cohere_prefix_ignores_jina_env(monkeypatch):
    """Test that explicit cohere prefix ignores JINA_AI_API_KEY env var."""
    monkeypatch.setenv("JINA_AI_API_KEY", "test-key")
    assert _detect_rerank_provider("rerank-v4.0-pro") == "cohere"
    assert _detect_rerank_provider("cohere/any-model") == "cohere"

@pytest.mark.parametrize("model", [
    "jina_ai/foo",
    "jina-bar",
])
def test_detect_rerank_provider_jina_prefix_ignores_missing_env(model, monkeypatch):
    """Test that explicit jina prefix works even if env var is missing."""
    monkeypatch.delenv("JINA_AI_API_KEY", raising=False)
    assert _detect_rerank_provider(model) == "jina"
