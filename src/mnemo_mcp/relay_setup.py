"""Credential resolution for mnemo-mcp.

Resolution order (relay only when ALL local sources are empty):
1. ENV VARS          -- User explicitly set (highest priority, skip everything)
2. RELAY CONFIG      -- Saved from previous relay setup (~/.config/mcp/config.enc)
3. RELAY SETUP       -- Interactive, ONLY when steps 1-2 are ALL empty (30s timeout)
4. LOCAL MODE        -- Fallback (Qwen3-Embedding ONNX)
"""

from __future__ import annotations

import os
import sys
from typing import Any

from loguru import logger

DEFAULT_RELAY_URL = "https://mnemo-mcp.n24q02m.com"
SERVER_NAME = "mnemo-mcp"
CLOUD_KEYS = [
    "JINA_AI_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
]
# All config keys that indicate a valid saved config
_ALL_CONFIG_KEYS = [*CLOUD_KEYS, "GOOGLE_DRIVE_CLIENT_ID"]

# Shorter timeout for optional-credential servers (user can skip)
RELAY_TIMEOUT_S = 300.0


def load_relay_config() -> dict[str, str] | None:
    """Try to load cloud config from encrypted config file.

    Only checks the config file -- env vars are handled by pydantic-settings
    in Settings. This is a synchronous, non-blocking check.

    Returns:
        Config dict with cloud API keys, or None if no config file found.
    """
    try:
        from mcp_relay_core.storage.config_file import read_config

        saved = read_config(SERVER_NAME)
        if saved and any(saved.get(k) for k in _ALL_CONFIG_KEYS):
            logger.info("Config loaded from file")
            return saved
        return None
    except Exception:
        return None


def apply_config(config: dict[str, str]) -> None:
    """Apply config dict to environment variables."""
    for key, value in config.items():
        if value and key not in os.environ:
            os.environ[key] = value
            logger.debug("Applied relay config: {}", key)


async def ensure_config() -> dict[str, str] | None:
    """Resolve config: env vars -> config file -> relay setup -> local fallback.

    Relay is ONLY triggered when steps 1-2 are ALL empty.
    Uses 300s timeout since mnemo-mcp works locally without credentials.

    Returns:
        Config dict with credential keys, or None if skipped/failed (local mode).
    """
    # 1 & 2. Check for existing credentials
    config = _check_local_credentials()
    if config is not None:
        # If config is empty dict, it means env vars are set (skip relay)
        return config if config else None

    # 3. No local credentials found -- trigger relay setup
    logger.info("No cloud credentials found. Starting relay setup...")

    relay_url = DEFAULT_RELAY_URL
    session = await _initiate_relay_session(relay_url)
    if not session:
        return None

    # Poll for result with shorter timeout
    try:
        from mcp_relay_core.relay.client import poll_for_result
        from mcp_relay_core.storage.config_file import write_config

        config = await poll_for_result(relay_url, session, timeout_s=RELAY_TIMEOUT_S)

        # Save to config file
        write_config(SERVER_NAME, config)
        logger.info("Cloud config saved successfully")

        apply_config(config)

        # Post-config setup (GDrive OAuth, notifications)
        await _handle_post_config_setup(relay_url, session)

        return config

    except RuntimeError as e:
        _handle_relay_error(e)
        return None


def _check_local_credentials() -> dict[str, str] | None:
    """Check if credentials already exist in env vars or config file.

    Returns:
        {} if env vars are present (skip relay),
        Config dict if config file is present,
        None if no credentials found (proceed to relay).
    """
    if any(os.environ.get(k) for k in CLOUD_KEYS):
        logger.info("Cloud API keys found in environment, skipping relay")
        return {}

    config = load_relay_config()
    if config is not None:
        return config

    return None


async def _initiate_relay_session(relay_url: str) -> Any | None:
    """Create a new relay session and print the setup URL."""
    try:
        from mcp_relay_core.relay.client import create_session

        from .relay_schema import RELAY_SCHEMA

        session = await create_session(relay_url, SERVER_NAME, RELAY_SCHEMA)  # ty: ignore[invalid-argument-type]

        # Log URL to stderr (visible to user in MCP client)
        print(
            f"\nConfigure cloud providers (optional, 30s timeout):"
            f"\n{session.relay_url}"
            f"\nSkip to use local mode (Qwen3-Embedding ONNX).\n",
            file=sys.stderr,
            flush=True,
        )
        return session
    except Exception:
        logger.debug("Cannot reach relay server at {}. Using local mode.", relay_url)
        return None


async def _handle_post_config_setup(relay_url: str, session: Any) -> None:
    """Handle Google Drive setup and relay status notifications after config is received."""
    # Notify relay page: config saved (info, NOT complete — GDrive OAuth follows)
    await _send_relay_message(
        relay_url,
        session.session_id,
        "info",
        "API keys saved. Starting Google Drive sync setup...",
    )

    # Trigger GDrive OAuth Device Code using default client ID from settings
    gdrive_ok = await _setup_gdrive_sync(relay_url, session)

    # NOW send complete (after GDrive OAuth finishes or skips)
    msg = (
        "Setup complete!"
        if gdrive_ok
        else "API keys saved. Google Drive sync can be configured later via config tool."
    )
    await _send_relay_message(relay_url, session.session_id, "complete", msg)


async def _setup_gdrive_sync(relay_url: str, session: Any) -> bool:
    """Trigger Google Drive OAuth setup if configured."""
    from mnemo_mcp.config import settings as _settings

    if not _settings.google_drive_client_id:
        return False

    logger.info("Starting Google Drive OAuth setup...")
    try:
        from mnemo_mcp.sync import setup_google_auth

        return await setup_google_auth(
            relay_url=relay_url,
            session_id=session.session_id,
        )
    except Exception as e:
        logger.warning(f"GDrive OAuth setup failed: {e}")
        return False


async def _send_relay_message(
    relay_url: str, session_id: str, msg_type: str, text: str
) -> None:
    """Send a status message to the relay server."""
    try:
        import httpx

        async with httpx.AsyncClient() as http:
            await http.post(
                f"{relay_url}/api/sessions/{session_id}/messages",
                json={"type": msg_type, "text": text},
            )
    except Exception:
        pass


def _handle_relay_error(e: RuntimeError) -> None:
    """Log relay error or skip/timeout message."""
    if "RELAY_SKIPPED" in str(e):
        logger.info("Relay setup skipped by user. Using local mode.")
    elif "timed out" in str(e).lower():
        logger.info("Relay setup timed out. Using local mode.")
    else:
        logger.debug("Relay setup ended: {}", e)
