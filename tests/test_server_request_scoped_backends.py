from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from mcp.server.fastmcp import Context

from mnemo_mcp.credential_state import _current_sub, store_for_sub
from mnemo_mcp.server import (
    _get_request_embedding,
    _get_request_reranker,
)


def _ctx() -> SimpleNamespace:
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context={}))


def _typed_ctx() -> Context:
    return cast(Context, _ctx())


def test_embedding_backend_is_scoped_to_current_sub(tmp_path, monkeypatch):
    monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))
    store_for_sub(
        "alice",
        {
            "EMBEDDING_MODELS": "cohere/embed-v4.0",
            "EMBEDDING_API_BASE": "https://alice.example/embed",
            "COHERE_API_KEY": "alice-key",
        },
    )

    token = _current_sub.set("alice")
    try:
        model, backend = _get_request_embedding(_typed_ctx(), "global-model", 768)
    finally:
        _current_sub.reset(token)

    assert model == "cohere/embed-v4.0"
    assert backend is not None
    assert backend.model == "cohere/embed-v4.0"
    assert backend.api_base == "https://alice.example/embed"
    assert backend.api_key == "alice-key"


def test_embedding_backend_does_not_fall_back_to_global_sub_config(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))

    token = _current_sub.set("missing-sub")
    try:
        model, backend = _get_request_embedding(_typed_ctx(), "global-model", 768)
    finally:
        _current_sub.reset(token)

    assert model is None
    assert backend is None


def test_reranker_backend_is_scoped_to_current_sub(tmp_path, monkeypatch):
    monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))
    store_for_sub(
        "bob",
        {
            "RERANK_MODELS": "cohere/rerank-v4.0-fast",
            "RERANK_API_BASE": "https://bob.example/rerank",
            "COHERE_API_KEY": "bob-key",
        },
    )

    token = _current_sub.set("bob")
    try:
        backend = _get_request_reranker(_typed_ctx())
    finally:
        _current_sub.reset(token)

    assert backend is not None
    assert backend.model == "cohere/rerank-v4.0-fast"
    assert backend.api_base == "https://bob.example/rerank"
    assert backend.api_key == "bob-key"
