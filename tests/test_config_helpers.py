"""Tests for mnemo_mcp.config helper functions (GPU detection, GGUF support)."""

import sys
from unittest.mock import MagicMock, patch

from mnemo_mcp.config import _detect_gpu, _has_gguf_support, _resolve_local_model


class TestDetectGPU:
    def test_cuda_available(self):
        """Returns True if CUDAExecutionProvider is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is True

    def test_dml_available(self):
        """Returns True if DmlExecutionProvider is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = [
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is True

    def test_no_gpu_provider(self):
        """Returns False if only CPUExecutionProvider is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is False

    def test_import_error(self):
        """Returns False if onnxruntime cannot be imported."""
        with patch.dict(sys.modules, {"onnxruntime": None}):
            # When sys.modules has None, import raises ModuleNotFoundError
            assert _detect_gpu() is False

    def test_runtime_exception(self):
        """Returns False if get_available_providers raises an exception."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.side_effect = Exception("Runtime error")
        with patch.dict(sys.modules, {"onnxruntime": mock_ort}):
            assert _detect_gpu() is False


class TestHasGGUFSupport:
    def test_llama_cpp_installed(self):
        """Returns True if llama_cpp is importable."""
        mock_llama = MagicMock()
        with patch.dict(sys.modules, {"llama_cpp": mock_llama}):
            assert _has_gguf_support() is True

    def test_llama_cpp_missing(self):
        """Returns False if llama_cpp cannot be imported."""
        with patch.dict(sys.modules, {"llama_cpp": None}):
            assert _has_gguf_support() is False


class TestResolveLocalModel:
    def test_gpu_and_gguf(self):
        """Returns GGUF model if GPU and llama_cpp are available."""
        with (
            patch("mnemo_mcp.config._detect_gpu", return_value=True),
            patch("mnemo_mcp.config._has_gguf_support", return_value=True),
        ):
            result = _resolve_local_model("onnx-model", "gguf-model")
            assert result == "gguf-model"

    def test_gpu_no_gguf(self):
        """Returns ONNX model if GPU available but no llama_cpp."""
        with (
            patch("mnemo_mcp.config._detect_gpu", return_value=True),
            patch("mnemo_mcp.config._has_gguf_support", return_value=False),
        ):
            result = _resolve_local_model("onnx-model", "gguf-model")
            assert result == "onnx-model"

    def test_no_gpu(self):
        """Returns ONNX model if no GPU (regardless of llama_cpp)."""
        with (
            patch("mnemo_mcp.config._detect_gpu", return_value=False),
            # Mock has_gguf to True to ensure it doesn't matter
            patch("mnemo_mcp.config._has_gguf_support", return_value=True),
        ):
            result = _resolve_local_model("onnx-model", "gguf-model")
            assert result == "onnx-model"
