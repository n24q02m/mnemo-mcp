"""Zero-env-config relay setup flow.

When no env vars are set, this module resolves config from the encrypted
config file or triggers the relay page setup to collect credentials from the
user via a browser-based form.

For mnemo-mcp, relay is optional -- local mode works without any config.
Proxy mode credentials are resolved via relay when LITELLM_PROXY_URL is not
set in env but the user wants cloud embeddings.
"""

from __future__ import annotations

import sys

from loguru import logger
from mcp_relay_core.relay.client import create_session, poll_for_result
from mcp_relay_core.storage.config_file import write_config
from mcp_relay_core.storage.resolver import resolve_config

from .relay_schema import RELAY_SCHEMA

DEFAULT_RELAY_URL = "https://mnemo-mcp.n24q02m.com"
REQUIRED_FIELDS = ["LITELLM_PROXY_URL"]
ALL_POSSIBLE_FIELDS = ["LITELLM_PROXY_URL", "LITELLM_PROXY_KEY"]


def load_relay_config() -> dict[str, str] | None:
    """Try to load proxy config from encrypted config file.

    Only checks the config file -- env vars are handled by pydantic-settings
    in Settings. This is a synchronous, non-blocking check.

    Returns:
        Config dict with LITELLM_PROXY_URL (and optionally LITELLM_PROXY_KEY),
        or None if no config file found.
    """
    result = resolve_config("mnemo-mcp", REQUIRED_FIELDS)
    if result.config is not None:
        logger.info("Relay config loaded from {}", result.source)
        return result.config
    return None


async def ensure_config() -> dict[str, str] | None:
    """Resolve proxy config or trigger relay setup.

    Resolution order:
    1. Encrypted config file (~/.config/mcp/config.enc)
    2. Relay setup (browser-based form via relay server)

    Returns:
        Config dict with credential keys, or None if setup fails/times out.

    Note:
        Environment variables are NOT checked here -- pydantic-settings in
        Settings already handles that. This function is only called when
        the user explicitly wants to configure proxy mode via the setup tool.
    """
    # Check config file
    config = load_relay_config()
    if config is not None:
        return config

    # No config found -- trigger relay setup
    logger.info("No proxy credentials found. Starting relay setup...")

    relay_url = DEFAULT_RELAY_URL
    try:
        session = await create_session(relay_url, "mnemo-mcp", RELAY_SCHEMA)
    except Exception:
        logger.warning(
            "Cannot reach relay server at {}. "
            "Set LITELLM_PROXY_URL manually or use local mode (default).",
            relay_url,
        )
        return None

    # Log URL to stderr (visible to user in MCP client)
    print(
        f"\nSetup required. Open this URL to configure:\n{session.relay_url}\n",
        file=sys.stderr,
        flush=True,
    )

    # Poll for result
    try:
        config = await poll_for_result(relay_url, session)
    except RuntimeError:
        logger.error("Relay setup timed out or session expired")
        return None

    # Save to config file
    write_config("mnemo-mcp", config)
    logger.info("Proxy config saved successfully")
    return config
