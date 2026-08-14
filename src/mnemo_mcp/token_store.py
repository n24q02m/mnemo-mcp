"""Local token storage for OAuth tokens.

Stores tokens in ~/.mnemo-mcp/tokens/<provider>.json with secure
file permissions (0600). Eliminates the need to paste long tokens
into MCP config -- tokens are persisted locally after the
first interactive OAuth flow.

Token lifecycle:
1. First run: no token -> Device Code OAuth flow -> token saved
2. Subsequent runs: token loaded from disk -> auto-refreshed when expired
3. Re-auth: delete token file -> next run triggers new OAuth flow
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from loguru import logger

from mnemo_mcp.config import settings
from mnemo_mcp.secure_file import ensure_owner_only_directory, write_owner_only


def _get_token_dir() -> Path:
    """Get directory for token storage (~/.mnemo-mcp/tokens/).

    Single-user (default) layout. Multi-user remote mode uses
    :func:`_get_token_dir_for_sub` so concurrent JWT subjects do not
    share a GDrive refresh-token.
    """
    return settings.get_data_dir() / "tokens"


def get_token_path(provider: str) -> Path:
    """Get path for a provider's token file."""
    return _get_token_dir() / f"{provider}.json"


def _get_token_dir_for_sub(sub: str) -> Path:
    """Per-sub token directory (``$MNEMO_DATA_DIR/subs/<hashed_sub>/tokens``).

    Multi-user remote mode (``PUBLIC_URL`` set) keys every artifact by
    JWT ``sub`` so user A's GDrive refresh-token is not visible to
    user B sharing the same mnemo-mcp deployment. The sub is hashed to
    prevent path traversal vulnerabilities.
    """
    safe_sub = hashlib.sha256(sub.encode("utf-8")).hexdigest()
    return settings.get_data_dir() / "subs" / safe_sub / "tokens"


def get_token_path_for_sub(sub: str, provider: str) -> Path:
    """Get path for a provider's token file scoped to a specific JWT sub."""
    return _get_token_dir_for_sub(sub) / f"{provider}.json"


def load_token(provider: str) -> dict | None:
    """Load stored OAuth token for a provider.

    Returns the token dict, or None if not found/invalid.
    """
    path = get_token_path(provider)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "access_token" in data:
            return data
        logger.warning(f"Invalid token format in {path}")
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load token from {path}: {e}")
        return None


def save_token(provider: str, token: dict) -> None:
    """Save OAuth token to local storage with secure permissions.

    File permissions: 0600 (owner read/write only)
    Directory permissions: 0700 (owner read/write/execute only)
    """
    data_dir = settings.get_data_dir()
    ensure_owner_only_directory(data_dir)
    token_dir = ensure_owner_only_directory(data_dir / "tokens")
    path = token_dir / f"{provider}.json"
    token_json = json.dumps(token, indent=2)
    write_owner_only(path, token_json.encode("utf-8"))

    logger.info(f"Token saved: {path}")


def delete_token(provider: str) -> bool:
    """Delete a stored token. Returns True if deleted."""
    path = get_token_path(provider)
    if path.exists():
        path.unlink()
        logger.info(f"Token deleted: {path}")
        return True
    return False


async def async_load_token(provider: str) -> dict | None:
    """Load stored OAuth token for a provider asynchronously."""
    return await asyncio.to_thread(load_token, provider)


async def async_save_token(provider: str, token: dict) -> None:
    """Save OAuth token to local storage asynchronously."""
    await asyncio.to_thread(save_token, provider, token)


async def async_delete_token(provider: str) -> bool:
    """Delete a stored token asynchronously. Returns True if deleted."""
    return await asyncio.to_thread(delete_token, provider)


def save_token_for_sub(sub: str, provider: str, token: dict) -> None:
    """Save OAuth token under the per-sub directory (multi-user remote).

    Same 0600 / 0700 hardening as :func:`save_token`. Token lands at
    ``$MNEMO_DATA_DIR/subs/<sub>/tokens/<provider>.json``.
    """
    data_dir = settings.get_data_dir()
    ensure_owner_only_directory(data_dir)
    subs_dir = ensure_owner_only_directory(data_dir / "subs")
    sub_dir = ensure_owner_only_directory(
        subs_dir / hashlib.sha256(sub.encode("utf-8")).hexdigest()
    )
    token_dir = ensure_owner_only_directory(sub_dir / "tokens")
    path = token_dir / f"{provider}.json"
    token_json = json.dumps(token, indent=2)
    write_owner_only(path, token_json.encode("utf-8"))

    logger.info(f"Token saved (sub={sub}): {path}")


def load_token_for_sub(sub: str, provider: str) -> dict | None:
    """Load a per-sub OAuth token. Returns None when absent or malformed."""
    path = get_token_path_for_sub(sub, provider)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "access_token" in data:
            return data
        logger.warning(f"Invalid token format in {path}")
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load token from {path}: {e}")
        return None


async def async_save_token_for_sub(sub: str, provider: str, token: dict) -> None:
    """Save per-sub OAuth token asynchronously."""
    await asyncio.to_thread(save_token_for_sub, sub, provider, token)


async def async_load_token_for_sub(sub: str, provider: str) -> dict | None:
    """Load per-sub OAuth token asynchronously."""
    return await asyncio.to_thread(load_token_for_sub, sub, provider)
