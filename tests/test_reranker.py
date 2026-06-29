import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import mnemo_mcp.reranker as reranker_mod
from mnemo_mcp.reranker import (
    CloudReranker,
    CohereReranker,
    FallbackChainReranker,
    Qwen3Reranker,
    _detect_rerank_provider,
    _strip_provider,
    build_default_rerank_chain,
    get_reranker,
    init_reranker,
)


def _rerank_resp(*results):
    """Build a litellm-shaped RerankResponse (resp.results)."""
    return SimpleNamespace(results=list(results))


@pytest.fixture(autouse=True)
def _reset_reranker_backend():
    """Reset module-level _backend before each test."""
    original = reranker_mod._backend
    reranker_mod._backend = None
    yield
    reranker_mod._backend = original


class TestUtilityFunctions:
    def test_detect_rerank_provider_jina(self):
        assert _detect_rerank_provider("jina-reranker-v3") == "jina"
        assert _detect_rerank_provider("jina_ai/model") == "jina"

    def test_detect_rerank_provider_env_fallback(self):
        # We need to make sure the model name DOES NOT start with 'rerank' or 'cohere/'
        # to trigger the environment variable check.
        with patch.dict(os.environ, {"JINA_AI_API_KEY": "test"}):
            assert _detect_rerank_provider("some-other-model") == "jina"

        with patch.dict(os.environ, {}, clear=True):
            assert _detect_rerank_provider("some-other-model") == "cohere"

    def test_detect_rerank_provider_cohere(self):
        assert _detect_rerank_provider("rerank-v4.0-pro") == "cohere"
        assert _detect_rerank_provider("cohere/model") == "cohere"

    def test_strip_provider(self):
        assert _strip_provider("jina_ai/model") == "model"
        assert _strip_provider("model") == "model"


class TestCohereReranker:
    def test_rerank_success(self):
        """Cloud reranker returns sorted (index, score) tuples."""
        reranker = CohereReranker(api_key="test-key")
        resp = _rerank_resp(
            SimpleNamespace(index=0, relevance_score=0.3),
            SimpleNamespace(index=1, relevance_score=0.9),
            SimpleNamespace(index=2, relevance_score=0.6),
        )

        with patch("mcp_core.llm.rerank", return_value=resp):
            results = reranker.rerank("test query", ["doc0", "doc1", "doc2"], top_n=2)

        assert len(results) == 2
        assert results[0] == (1, 0.9)
        assert results[1] == (2, 0.6)

    def test_rerank_with_dict_results(self):
        """Cloud reranker handles dict-style results."""
        reranker = CohereReranker(api_key="test-key")
        resp = _rerank_resp(
            {"index": 0, "relevance_score": 0.8},
            {"index": 1, "relevance_score": 0.5},
        )

        with patch("mcp_core.llm.rerank", return_value=resp):
            results = reranker.rerank("query", ["doc0", "doc1"])

        assert results[0] == (0, 0.8)
        assert results[1] == (1, 0.5)

    def test_rerank_none_results_guarded(self):
        """litellm RerankResponse.results defaults to None -> empty list."""
        reranker = CohereReranker(api_key="test-key")
        resp = SimpleNamespace(results=None)

        with patch("mcp_core.llm.rerank", return_value=resp):
            results = reranker.rerank("query", ["doc"])

        assert results == []

    def test_rerank_empty_docs(self):
        """Empty documents list returns empty results."""
        reranker = CohereReranker(api_key="test-key")
        results = reranker.rerank("query", [])
        assert results == []

    def test_rerank_failure_returns_empty(self):
        """Reranker returns empty list on failure (never raises)."""
        reranker = CohereReranker(api_key="test-key")

        with patch("mcp_core.llm.rerank", side_effect=Exception("API error")):
            results = reranker.rerank("query", ["doc"])

        assert results == []

    def test_check_available_success(self):
        """check_available returns True when API responds."""
        reranker = CohereReranker(api_key="test-key")
        resp = _rerank_resp(SimpleNamespace(index=0, relevance_score=0.5))

        with patch("mcp_core.llm.rerank", return_value=resp):
            assert reranker.check_available() is True

    def test_check_available_empty(self):
        """check_available returns False when API returns empty results."""
        reranker = CohereReranker(api_key="test-key")
        resp = _rerank_resp()

        with patch("mcp_core.llm.rerank", return_value=resp):
            assert reranker.check_available() is False

    @pytest.mark.parametrize(
        "msg",
        [
            "401 unauthorized",
            "403 forbidden",
            "invalid api key",
            "unauthorized",
            "bad api key",
        ],
    )
    def test_check_available_auth_errors(self, msg):
        """check_available logs warning for auth errors."""
        reranker = CohereReranker(api_key="bad-key")

        with patch("mcp_core.llm.rerank", side_effect=Exception(msg)):
            assert reranker.check_available() is False

    def test_check_available_generic_error(self):
        """check_available logs debug for non-auth errors."""
        reranker = CohereReranker(api_key="test-key")

        with patch("mcp_core.llm.rerank", side_effect=Exception("connection error")):
            assert reranker.check_available() is False

    def test_litellm_model_mapping(self):
        """Bare jina/cohere names map to litellm provider/model form."""
        assert CloudReranker(model="rerank-v4.0-pro")._litellm_model() == (
            "cohere/rerank-v4.0-pro"
        )
        assert CloudReranker(model="jina-reranker-v3")._litellm_model() == (
            "jina_ai/jina-reranker-v3"
        )
        assert CloudReranker(model="cohere/rerank-v4.0-pro")._litellm_model() == (
            "cohere/rerank-v4.0-pro"
        )


class TestQwen3Reranker:
    def test_rerank_success(self):
        """Local reranker returns sorted (index, score) tuples."""
        reranker = Qwen3Reranker()

        mock_model = MagicMock()
        mock_model.rerank.return_value = [0.3, 0.9, 0.6]

        with patch.object(reranker, "_get_model", return_value=mock_model):
            results = reranker.rerank("query", ["doc0", "doc1", "doc2"], top_n=2)

        assert len(results) == 2
        assert results[0] == (1, 0.9)
        assert results[1] == (2, 0.6)

    def test_rerank_empty_docs(self):
        """Empty documents list returns empty results."""
        reranker = Qwen3Reranker()
        results = reranker.rerank("query", [])
        assert results == []

    def test_rerank_failure_returns_empty(self):
        """Local reranker returns empty list on failure."""
        reranker = Qwen3Reranker()

        mock_model = MagicMock()
        mock_model.rerank.side_effect = RuntimeError("ONNX error")

        with patch.object(reranker, "_get_model", return_value=mock_model):
            results = reranker.rerank("query", ["doc"])

        assert results == []

    def test_check_available_success(self):
        """check_available returns True when model loads."""
        reranker = Qwen3Reranker()

        mock_model = MagicMock()
        mock_model.rerank.return_value = [0.5]

        with patch.object(reranker, "_get_model", return_value=mock_model):
            assert reranker.check_available() is True

    def test_check_available_failure(self):
        """check_available returns False when model fails."""
        reranker = Qwen3Reranker()

        with patch.object(
            reranker, "_get_model", side_effect=ImportError("no qwen3_embed")
        ):
            assert reranker.check_available() is False

    def test_check_available_empty_scores(self):
        """check_available returns False if model returns no scores."""
        reranker = Qwen3Reranker()
        mock_model = MagicMock()
        mock_model.rerank.return_value = []
        with patch.object(reranker, "_get_model", return_value=mock_model):
            assert reranker.check_available() is False

    def test_lazy_load_and_caching(self):
        """Model is not loaded until _get_model is called, and is cached."""
        reranker = Qwen3Reranker()
        assert reranker._model is None

        # Bolt Performance Optimization: mock the module instead of importing to avoid numpy re-import issues
        mock_encoder_cls = MagicMock()
        with patch.dict(sys.modules, {"qwen3_embed": MagicMock()}):
            import qwen3_embed

            qwen3_embed.TextCrossEncoder = mock_encoder_cls

            model1 = reranker._get_model()
            assert reranker._model is not None
            model2 = reranker._get_model()
            assert model1 is model2
            mock_encoder_cls.assert_called_once()


class TestFallbackChainReranker:
    def test_init_empty_raises(self):
        with pytest.raises(ValueError, match="requires at least one backend"):
            FallbackChainReranker([])

    def test_rerank_fallback_on_exception(self):
        b1 = MagicMock(spec=CloudReranker)
        b1.rerank.side_effect = Exception("Fail")
        b2 = MagicMock(spec=CloudReranker)
        b2.rerank.return_value = [(0, 0.9)]

        chain = FallbackChainReranker([b1, b2])
        assert chain.rerank("q", ["d"]) == [(0, 0.9)]
        b1.rerank.assert_called_once()
        b2.rerank.assert_called_once()

    def test_rerank_fallback_on_empty(self):
        b1 = MagicMock(spec=CloudReranker)
        b1.rerank.return_value = []
        b2 = MagicMock(spec=CloudReranker)
        b2.rerank.return_value = [(0, 0.9)]

        chain = FallbackChainReranker([b1, b2])
        assert chain.rerank("q", ["d"]) == [(0, 0.9)]

    def test_rerank_all_fail(self):
        b1 = MagicMock(spec=CloudReranker)
        b1.rerank.return_value = []
        b2 = MagicMock(spec=CloudReranker)
        b2.rerank.side_effect = Exception("Fail")

        chain = FallbackChainReranker([b1, b2])
        assert chain.rerank("q", ["d"]) == []

    def test_rerank_empty_docs(self):
        chain = FallbackChainReranker([MagicMock()])
        assert chain.rerank("q", []) == []

    def test_check_available_any(self):
        b1 = MagicMock()
        b1.check_available.return_value = False
        b2 = MagicMock()
        b2.check_available.return_value = True

        chain = FallbackChainReranker([b1, b2])
        assert chain.check_available() is True

    def test_check_available_exception_guarded(self):
        b1 = MagicMock()
        b1.check_available.side_effect = Exception("error")
        b2 = MagicMock()
        b2.check_available.return_value = False

        chain = FallbackChainReranker([b1, b2])
        assert chain.check_available() is False


class TestBuildChain:
    def test_build_default_chain_order(self):
        with patch.dict(os.environ, {"JINA_AI_API_KEY": "j", "COHERE_API_KEY": "c"}):
            chain = build_default_rerank_chain(prefer_local=True)
            assert isinstance(chain._backends[0], Qwen3Reranker)
            assert isinstance(chain._backends[1], CloudReranker)
            assert "jina" in chain._backends[1].model

            chain = build_default_rerank_chain(prefer_local=False)
            assert isinstance(chain._backends[0], CloudReranker)
            assert isinstance(chain._backends[-1], Qwen3Reranker)

    def test_build_chain_env_filtering(self):
        with patch.dict(os.environ, {"CO_API_KEY": "c"}, clear=True):
            chain = build_default_rerank_chain()
            # Qwen3 + 1 cloud (cohere)
            assert len(chain._backends) == 2
            assert any(
                "rerank" in b.model for b in chain._backends if hasattr(b, "model")
            )


class TestInitReranker:
    def test_init_cloud(self):
        backend = init_reranker("cloud", "rerank-v4.0-pro")
        assert isinstance(backend, CohereReranker)
        assert get_reranker() is backend

    def test_init_unknown_backend(self):
        with pytest.raises(ValueError, match="Unknown reranker backend"):
            init_reranker("invalid")


class TestMiscCoverage:
    def test_init_local(self):
        backend = init_reranker("local", "custom/model")
        assert isinstance(backend, Qwen3Reranker)
        assert backend._model_name == "custom/model"

    def test_build_chain_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            chain = build_default_rerank_chain()
            # Only local qwen3
            assert len(chain._backends) == 1
            assert isinstance(chain._backends[0], Qwen3Reranker)

    def test_build_chain_jina_only(self):
        with patch.dict(os.environ, {"JINA_AI_API_KEY": "j"}, clear=True):
            chain = build_default_rerank_chain()
            assert len(chain._backends) == 2
            assert any(
                "jina" in b.model for b in chain._backends if hasattr(b, "model")
            )
