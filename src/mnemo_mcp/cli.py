"""Console-script entry: mounts the shared mcp_core CLI builder.

Bare invocation and any leading-dash argv (e.g. --http) start the server
exactly as before; subcommands run one-shot operator actions.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from mcp_core import build_cli


def _serve(argv: list[str]) -> int | None:
    from mnemo_mcp.server import main as server_main

    server_main()
    return 0


def _configure_auth(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "provider", choices=["google"], help="Credential provider to authorize"
    )


def _handle_auth(args: argparse.Namespace) -> int:
    from mnemo_mcp.setup_tool import run_setup_sync

    result = asyncio.run(run_setup_sync())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "authenticated" else 1


def _handle_warmup(args: argparse.Namespace) -> int:
    from mnemo_mcp.setup_tool import run_warmup

    result = asyncio.run(run_warmup())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


def _extras() -> dict:
    return {
        "auth": (_configure_auth, _handle_auth),
        "warmup": _handle_warmup,
    }


def _version() -> str:
    from mnemo_mcp import __version__

    return __version__


def main() -> int:
    return build_cli("mnemo-mcp", serve=_serve, extra=_extras(), version=_version())(
        None
    )
