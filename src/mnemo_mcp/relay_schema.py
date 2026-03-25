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
            "id": "proxy",
            "label": "Proxy Mode",
            "description": "Use a LiteLLM proxy for cloud embeddings and LLM features.",
            "fields": [
                {
                    "key": "LITELLM_PROXY_URL",
                    "label": "LiteLLM Proxy URL",
                    "type": "url",
                    "placeholder": "http://10.0.0.20:4000",
                    "helpText": "URL of your LiteLLM proxy server",
                },
                {
                    "key": "LITELLM_PROXY_KEY",
                    "label": "Proxy Key",
                    "type": "password",
                    "placeholder": "sk-...",
                    "helpText": "Virtual key for the proxy (optional)",
                    "required": False,
                },
            ],
        },
    ],
}
