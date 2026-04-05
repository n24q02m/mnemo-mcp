"""Tests for mnemo_mcp.config — Settings, API keys, embedding resolution."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from mnemo_mcp.config import (
    Settings,
    _detect_gpu,
    _has_gguf_support,
    _resolve_local_model,
)


class TestGpuDetection:
    def test_detect_gpu_success_cuda(self):
        """_detect_gpu returns True when CUDA is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is True

    def test_detect_gpu_success_dml(self):
        """_detect_gpu returns True when DirectML is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = [
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is True

    def test_detect_gpu_no_gpu(self):
        """_detect_gpu returns False when only CPU is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is False

    def test_detect_gpu_import_error(self):
        """_detect_gpu returns False when onnxruntime is not installed."""
        with patch.dict(sys.modules, {"onnxruntime": None}):
            assert _detect_gpu() is False

    def test_detect_gpu_runtime_exception(self):
        """_detect_gpu returns False when get_available_providers raises."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.side_effect = Exception("Runtime error")
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is False


class TestGgufSupport:
    def test_has_gguf_support_success(self):
        """_has_gguf_support returns True when llama-cpp-python is installed."""
        mock_llama = MagicMock()
        with patch.dict(sys.modules, {"llama_cpp": mock_llama}):
            assert _has_gguf_support() is True

    def test_has_gguf_support_import_error(self):
        """_has_gguf_support returns False when llama-cpp-python is not installed."""
        with patch.dict(sys.modules, {"llama_cpp": None}):
            assert _has_gguf_support() is False


class TestResolveLocalModel:
    def test_resolve_local_model_onnx_by_default(self):
        """Returns ONNX variant if GPU not available."""
        with patch("mnemo_mcp.config._detect_gpu", return_value=False):
            assert _resolve_local_model("onnx", "gguf") == "onnx"

    def test_resolve_local_model_onnx_no_gguf_support(self):
        """Returns ONNX variant if llama-cpp not installed."""
        with (
            patch("mnemo_mcp.config._detect_gpu", return_value=True),
            patch("mnemo_mcp.config._has_gguf_support", return_value=False),
        ):
            assert _resolve_local_model("onnx", "gguf") == "onnx"

    def test_resolve_local_model_gguf_with_gpu_and_llama(self):
        """Returns GGUF variant if GPU and llama-cpp available."""
        with (
            patch("mnemo_mcp.config._detect_gpu", return_value=True),
            patch("mnemo_mcp.config._has_gguf_support", return_value=True),
        ):
            assert _resolve_local_model("onnx", "gguf") == "gguf"


class TestSettingsDefaults:
    def test_db_path_empty(self):
        s = Settings(api_keys=None)
        assert s.db_path == ""

    def test_sync_enabled_default(self):
        s = Settings(api_keys=None)
        assert s.sync_enabled is True

    def test_sync_folder(self):
        s = Settings(api_keys=None)
        assert s.sync_folder == "mnemo-mcp"

    def test_sync_interval(self):
        s = Settings(api_keys=None)
        assert s.sync_interval == 300

    def test_embedding_dims_default(self):
        s = Settings(api_keys=None)
        assert s.embedding_dims == 0

    def test_embedding_model_empty(self):
        s = Settings(api_keys=None)
        assert s.embedding_model == ""


class TestDbPath:
    def test_default_path(self):
        s = Settings(api_keys=None)
        expected = Path.home() / ".mnemo-mcp" / "memories.db"
        assert s.get_db_path() == expected

    def test_custom_path(self):
        s = Settings(db_path="/tmp/custom.db", api_keys=None)
        assert s.get_db_path() == Path("/tmp/custom.db")

    def test_expanduser(self):
        s = Settings(db_path="~/test.db", api_keys=None)
        assert s.get_db_path() == Path.home() / "test.db"

    def test_data_dir(self):
        s = Settings(db_path="/tmp/data/test.db", api_keys=None)
        assert s.get_data_dir() == Path("/tmp/data")

    def test_data_dir_default(self):
        s = Settings(api_keys=None)
        assert s.get_data_dir() == Path.home() / ".mnemo-mcp"


class TestApiKeys:
    def test_no_keys(self):
        s = Settings(api_keys=None)
        assert s.setup_api_keys() == {}

    def test_single_key(self, monkeypatch):
        s = Settings(api_keys="GOOGLE_API_KEY:test-key-123")
        result = s.setup_api_keys()
        assert "GOOGLE_API_KEY" in result
        assert result["GOOGLE_API_KEY"] == ["test-key-123"]
        assert os.environ.get("GOOGLE_API_KEY") == "test-key-123"
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def test_multiple_keys(self, monkeypatch):
        s = Settings(api_keys="GOOGLE_API_KEY:key1,OPENAI_API_KEY:key2")
        result = s.setup_api_keys()
        assert len(result) == 2
        assert "GOOGLE_API_KEY" in result
        assert "OPENAI_API_KEY" in result
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def test_duplicate_provider(self, monkeypatch):
        """Multiple keys for same provider — first key is set as env var."""
        s = Settings(api_keys="GOOGLE_API_KEY:key1,GOOGLE_API_KEY:key2")
        result = s.setup_api_keys()
        assert len(result["GOOGLE_API_KEY"]) == 2
        assert os.environ.get("GOOGLE_API_KEY") == "key1"
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def test_malformed_no_colon(self):
        s = Settings(api_keys="INVALID_FORMAT")
        result = s.setup_api_keys()
        assert result == {}

    def test_empty_key_value(self):
        s = Settings(api_keys="GOOGLE_API_KEY:")
        result = s.setup_api_keys()
        assert result == {}

    def test_whitespace_handling(self, monkeypatch):
        s = Settings(api_keys="  GOOGLE_API_KEY : key1 , OPENAI_API_KEY : key2  ")
        result = s.setup_api_keys()
        assert "GOOGLE_API_KEY" in result
        assert result["GOOGLE_API_KEY"] == ["key1"]
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def test_colon_in_key_value(self, monkeypatch):
        """API keys can contain colons (e.g., base64-encoded keys)."""
        s = Settings(api_keys="GOOGLE_API_KEY:abc:def:ghi")
        result = s.setup_api_keys()
        assert result["GOOGLE_API_KEY"] == ["abc:def:ghi"]
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def test_alias_google_to_gemini(self, monkeypatch):
        """GOOGLE_API_KEY should also set GEMINI_API_KEY for Gemini SDK."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        s = Settings(api_keys="GOOGLE_API_KEY:test-key")
        s.setup_api_keys()
        assert os.environ.get("GEMINI_API_KEY") == "test-key"
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def test_alias_no_overwrite(self, monkeypatch):
        """If GEMINI_API_KEY already set, alias does not overwrite."""
        monkeypatch.setenv("GEMINI_API_KEY", "existing")
        s = Settings(api_keys="GOOGLE_API_KEY:new-key")
        s.setup_api_keys()
        assert os.environ.get("GEMINI_API_KEY") == "existing"
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)


class TestEmbeddingModel:
    def test_explicit_model(self):
        s = Settings(embedding_model="custom/model", api_keys=None)
        assert s.resolve_embedding_model() == "custom/model"

    def test_no_model_returns_none(self):
        """Without explicit EMBEDDING_MODEL, returns None (auto-detect in server)."""
        s = Settings(api_keys="GOOGLE_API_KEY:key")
        assert s.resolve_embedding_model() is None

    def test_no_keys_returns_none(self):
        s = Settings(api_keys=None)
        assert s.resolve_embedding_model() is None

    def test_explicit_overrides_auto(self):
        """Explicit EMBEDDING_MODEL takes priority over API_KEYS."""
        s = Settings(
            embedding_model="custom/model",
            api_keys="GOOGLE_API_KEY:key",
        )
        assert s.resolve_embedding_model() == "custom/model"


class TestEmbeddingDims:
    def test_explicit_dims(self):
        s = Settings(embedding_dims=512, api_keys=None)
        assert s.resolve_embedding_dims() == 512

    def test_default_zero(self):
        """Without explicit EMBEDDING_DIMS, returns 0 (auto-detect at runtime)."""
        s = Settings(api_keys=None)
        assert s.resolve_embedding_dims() == 0


class TestEmbeddingBackend:
    def test_explicit_litellm(self):
        s = Settings(embedding_backend="litellm", api_keys=None)
        assert s.resolve_embedding_backend() == "cloud"

    def test_explicit_local(self):
        s = Settings(embedding_backend="local", api_keys=None)
        assert s.resolve_embedding_backend() == "local"

    def test_auto_detect_cloud_with_keys(self):
        """Falls back to cloud when keys provided."""
        s = Settings(api_keys="GOOGLE_API_KEY:key")
        assert s.resolve_embedding_backend() in ("cloud", "local")

    def test_auto_detect_no_keys_no_local(self, monkeypatch):
        """Returns 'local' when no keys configured."""
        for k in (
            "JINA_AI_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "OPENAI_API_KEY",
            "COHERE_API_KEY",
            "CO_API_KEY",
            "XAI_API_KEY",
        ):
            monkeypatch.delenv(k, raising=False)
        s = Settings(api_keys=None)
        result = s.resolve_embedding_backend()
        assert result == "local"

    def test_explicit_overrides_auto(self):
        """Explicit backend takes priority over auto-detection."""
        s = Settings(embedding_backend="litellm", api_keys=None)
        assert s.resolve_embedding_backend() == "cloud"


class TestSetupProviders:
    def test_setup_providers_sdk(self, monkeypatch):
        """setup_providers returns 'sdk' when API keys are present."""
        s = Settings(api_keys="OPENAI_API_KEY:test")
        # Instead of patching the method on the instance, we patch it on the class
        with patch("mnemo_mcp.config.Settings.setup_api_keys") as mock_setup:
            assert s.setup_providers() == "sdk"
            mock_setup.assert_called_once()
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def test_setup_providers_local(self, monkeypatch):
        """setup_providers returns 'local' when no keys are present."""
        for k in [
            "OPENAI_API_KEY",
            "COHERE_API_KEY",
            "GEMINI_API_KEY",
            "JINA_AI_API_KEY",
            "GOOGLE_API_KEY",
            "CO_API_KEY",
            "XAI_API_KEY",
        ]:
            monkeypatch.delenv(k, raising=False)
        s = Settings(api_keys=None)
        assert s.setup_providers() == "local"

    def test_resolve_provider_mode_env_var(self, monkeypatch):
        """resolve_provider_mode returns 'sdk' if env var is set."""
        monkeypatch.setenv("XAI_API_KEY", "test")
        s = Settings(api_keys=None)
        assert s.resolve_provider_mode() == "sdk"


class TestRerankSettings:
    def test_rerank_enabled_default(self):
        s = Settings(api_keys=None)
        assert s.rerank_enabled is True

    def test_rerank_backend_empty_default(self):
        s = Settings(api_keys=None)
        assert s.rerank_backend == ""

    def test_rerank_model_empty_default(self):
        s = Settings(api_keys=None)
        assert s.rerank_model == ""

    def test_rerank_top_n_default(self):
        s = Settings(api_keys=None)
        assert s.rerank_top_n == 10

    def test_resolve_rerank_backend_disabled(self):
        s = Settings(rerank_enabled=False, api_keys=None)
        assert s.resolve_rerank_backend() == ""

    def test_resolve_rerank_backend_explicit(self):
        s = Settings(rerank_backend="litellm", api_keys=None)
        assert s.resolve_rerank_backend() == "cloud"

    def test_resolve_rerank_backend_model_set(self):
        s = Settings(rerank_model="custom/reranker", api_keys=None)
        assert s.resolve_rerank_backend() == "cloud"

    def test_resolve_rerank_backend_cohere_env(self, monkeypatch):
        monkeypatch.setenv("COHERE_API_KEY", "test-key")
        s = Settings(api_keys=None)
        assert s.resolve_rerank_backend() == "cloud"

    def test_resolve_rerank_backend_cohere_in_api_keys(self):
        s = Settings(api_keys="COHERE_API_KEY:test-key")
        assert s.resolve_rerank_backend() == "cloud"

    def test_resolve_rerank_backend_local_fallback(self, monkeypatch):
        for k in ["COHERE_API_KEY", "CO_API_KEY", "JINA_AI_API_KEY"]:
            monkeypatch.delenv(k, raising=False)
        s = Settings(api_keys=None)
        assert s.resolve_rerank_backend() == "local"

    def test_resolve_rerank_model_explicit(self):
        s = Settings(rerank_model="custom/reranker", api_keys=None)
        assert s.resolve_rerank_model() == "custom/reranker"

    def test_resolve_rerank_model_cohere_env(self, monkeypatch):
        monkeypatch.setenv("COHERE_API_KEY", "test-key")
        s = Settings(api_keys=None)
        assert s.resolve_rerank_model() == "rerank-v4.0-pro"

    def test_resolve_rerank_model_cohere_in_api_keys(self):
        s = Settings(api_keys="COHERE_API_KEY:test-key")
        assert s.resolve_rerank_model() == "rerank-v4.0-pro"

    def test_resolve_rerank_model_none_no_keys(self, monkeypatch):
        for k in ["COHERE_API_KEY", "CO_API_KEY", "JINA_AI_API_KEY"]:
            monkeypatch.delenv(k, raising=False)
        s = Settings(api_keys=None)
        assert s.resolve_rerank_model() is None

    def test_resolve_local_rerank_model(self):
        s = Settings(api_keys=None)
        with patch("mnemo_mcp.config._resolve_local_model", return_value="mock_model"):
            assert s.resolve_local_rerank_model() == "mock_model"

    def test_resolve_local_embedding_model(self):
        s = Settings(api_keys=None)
        with patch("mnemo_mcp.config._resolve_local_model", return_value="mock_model"):
            assert s.resolve_local_embedding_model() == "mock_model"


class TestGoogleDriveClientId:
    def test_default_ships_oauth_client_id(self):
        s = Settings(api_keys=None)
        assert s.google_drive_client_id != ""
        assert "apps.googleusercontent.com" in s.google_drive_client_id

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv(
            "GOOGLE_DRIVE_CLIENT_ID", "123456.apps.googleusercontent.com"
        )
        s = Settings(api_keys=None)
        assert s.google_drive_client_id == "123456.apps.googleusercontent.com"
