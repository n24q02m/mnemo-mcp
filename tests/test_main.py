"""Tests for mnemo_mcp.__main__."""

import sys
from unittest.mock import patch

from mnemo_mcp.__main__ import _cli


def test_cli_default_server():
    """Test default CLI behavior: calls server.main()."""
    with (
        patch.object(sys, "argv", ["mnemo-mcp"]),
        patch("mnemo_mcp.server.main") as mock_server_main,
    ):
        _cli()
        mock_server_main.assert_called_once()


def test_cli_server_explicit():
    """Test explicit server behavior: calls server.main()."""
    with (
        patch.object(sys, "argv", ["mnemo-mcp", "server"]),
        patch("mnemo_mcp.server.main") as mock_server_main,
    ):
        _cli()
        mock_server_main.assert_called_once()


def test_cli_setup_sync_default():
    """Test setup-sync default behavior: calls setup_sync('drive')."""
    with (
        patch.object(sys, "argv", ["mnemo-mcp", "setup-sync"]),
        patch("mnemo_mcp.sync.setup_sync") as mock_setup_sync,
    ):
        _cli()
        mock_setup_sync.assert_called_once_with("drive")


def test_cli_setup_sync_custom():
    """Test setup-sync custom behavior: calls setup_sync('s3')."""
    with (
        patch.object(sys, "argv", ["mnemo-mcp", "setup-sync", "s3"]),
        patch("mnemo_mcp.sync.setup_sync") as mock_setup_sync,
    ):
        _cli()
        mock_setup_sync.assert_called_once_with("s3")
