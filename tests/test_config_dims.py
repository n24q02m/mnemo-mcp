"""Tests for mnemo_mcp.config — Model dimensions."""

from mnemo_mcp.config import Settings


class TestModelDims:
    def test_known_models(self):
        s = Settings(api_keys=None)
        assert s.get_model_dims("gemini/text-embedding-004") == 768
        assert s.get_model_dims("text-embedding-3-small") == 1536
        assert s.get_model_dims("text-embedding-3-large") == 3072
        assert s.get_model_dims("text-embedding-ada-002") == 1536
        assert s.get_model_dims("mistral/mistral-embed") == 1024

    def test_unknown_model_default(self):
        s = Settings(api_keys=None)
        assert s.get_model_dims("unknown-model") == 768
