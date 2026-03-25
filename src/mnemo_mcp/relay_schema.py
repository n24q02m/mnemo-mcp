"""Config schema for relay page setup."""

from mcp_relay_core.schema.types import RelayConfigSchema

RELAY_SCHEMA: RelayConfigSchema = {
    "server": "mnemo-mcp",
    "displayName": "Mnemo MCP",
    "modes": [
        {
            "id": "local",
            "label": "Local Mode",
            "description": "Default. Uses local ONNX embeddings + SQLite. No config needed.",
            "fields": [],
        },
        {
            "id": "cloud",
            "label": "Cloud Mode",
            "description": "Use cloud API keys for embeddings (Jina > Gemini > OpenAI > Cohere).",
            "fields": [
                {
                    "key": "API_KEYS",
                    "label": "API Keys",
                    "type": "password",
                    "placeholder": "JINA_AI_API_KEY:jina_...,GEMINI_API_KEY:AIza...",
                    "helpText": "Format: ENV_VAR:key,ENV_VAR:key (Jina > Gemini > OpenAI > Cohere priority)",
                },
            ],
        },
    ],
}
