"""Configuration settings for Mnemo MCP Server."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _default_data_dir() -> Path:
    """Get default data directory (~/.mnemo-mcp/)."""
    return Path.home() / ".mnemo-mcp"


class Settings(BaseSettings):
    """Mnemo MCP Server configuration.

    Environment variables:
    - DB_PATH: Path to SQLite database (default: ~/.mnemo-mcp/memories.db)
    - API_KEYS: Provider API keys (format: ENV_VAR:key,ENV_VAR:key)
    - EMBEDDING_MODEL: LiteLLM embedding model (auto-detected if not set)
    - EMBEDDING_DIMS: Embedding dimensions (auto-detected)
    - SYNC_ENABLED: Enable rclone sync (default: false)
    - SYNC_REMOTE: Rclone remote name (e.g., "gdrive")
    - SYNC_FOLDER: Remote folder name (default: "mnemo-mcp")
    - SYNC_INTERVAL: Auto-sync interval in seconds (0 = manual only)
    """

    # Database
    db_path: str = ""

    # LLM API Keys: "ENV_VAR:key,ENV_VAR:key,..."
    api_keys: str | None = None

    # Embedding model (LiteLLM format, auto-detected from API_KEYS if not set)
    embedding_model: str = ""
    embedding_dims: int = 0  # 0 = auto-detect

    # Sync (rclone)
    sync_enabled: bool = False
    sync_remote: str = ""  # rclone remote name
    sync_folder: str = "mnemo-mcp"
    sync_interval: int = 0  # seconds, 0 = manual only

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "", "case_sensitive": False}

    def get_db_path(self) -> Path:
        """Get resolved database path."""
        if self.db_path:
            return Path(self.db_path).expanduser()
        return _default_data_dir() / "memories.db"

    def get_data_dir(self) -> Path:
        """Get data directory (parent of db file)."""
        return self.get_db_path().parent

    def setup_api_keys(self) -> dict[str, list[str]]:
        """Parse API_KEYS and set env vars for LiteLLM.

        Format: "GOOGLE_API_KEY:AIza...,OPENAI_API_KEY:sk-..."

        Returns:
            Dict mapping env var name to list of API keys.
        """
        if not self.api_keys:
            return {}

        keys_by_env: dict[str, list[str]] = {}

        for pair in self.api_keys.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue

            env_var, key = pair.split(":", 1)
            env_var = env_var.strip()
            key = key.strip()

            if not key:
                continue

            keys_by_env.setdefault(env_var, []).append(key)

        # Set first key of each env var (LiteLLM reads from env)
        for env_var, keys in keys_by_env.items():
            if keys:
                os.environ[env_var] = keys[0]

        return keys_by_env

    def resolve_embedding_model(self) -> str | None:
        """Auto-detect embedding model from API_KEYS if not explicitly set.

        Priority:
        1. Explicit EMBEDDING_MODEL env var
        2. Infer from API keys:
           - GOOGLE_API_KEY → gemini/text-embedding-004
           - OPENAI_API_KEY → text-embedding-3-small
           - MISTRAL_API_KEY → mistral/mistral-embed
           - COHERE_API_KEY → cohere/embed-english-v3.0
        3. None (embeddings disabled, FTS5-only mode)
        """
        if self.embedding_model:
            return self.embedding_model

        if not self.api_keys:
            return None

        # Check which providers are configured
        for pair in self.api_keys.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            env_var = pair.split(":", 1)[0].strip().upper()

            if env_var == "GOOGLE_API_KEY":
                return "gemini/text-embedding-004"
            elif env_var == "OPENAI_API_KEY":
                return "text-embedding-3-small"
            elif env_var == "MISTRAL_API_KEY":
                return "mistral/mistral-embed"
            elif env_var == "COHERE_API_KEY":
                return "cohere/embed-english-v3.0"

        return None

    def resolve_embedding_dims(self, model: str | None) -> int:
        """Get embedding dimensions for a model.

        Returns explicit EMBEDDING_DIMS if set, otherwise infers from model.
        """
        if self.embedding_dims > 0:
            return self.embedding_dims

        if not model:
            return 0

        # Known dimensions for common models
        dims_map = {
            "gemini/text-embedding-004": 768,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "mistral/mistral-embed": 1024,
            "cohere/embed-english-v3.0": 1024,
            # Ollama models
            "ollama/nomic-embed-text": 768,
            "ollama/mxbai-embed-large": 1024,
            "ollama/all-minilm": 384,
        }

        return dims_map.get(model, 768)  # Default 768


settings = Settings()
