from unittest.mock import MagicMock, patch

import pytest


def test_credential_state_store_for_sub_fchmod_propagates(tmp_path):
    import mnemo_mcp.credential_state

    with (
        patch("mnemo_mcp.credential_state._sub_data_dir", return_value=tmp_path),
        patch("mnemo_mcp.credential_state.os.name", "posix"),
        patch("mnemo_mcp.credential_state.os.fchmod", side_effect=OSError("fchmod failed")),
        pytest.raises(OSError, match="fchmod failed")
    ):
        mnemo_mcp.credential_state.store_for_sub("sub123", {"key": "val"})

def test_gdrive_save_folder_id_fchmod_propagates(tmp_path):
    import asyncio

    from mnemo_mcp.sync.gdrive import _save_folder_id

    with (
        patch("mnemo_mcp.sync.gdrive.settings") as mock_settings,
        patch("os.name", "posix"),
        patch("os.fchmod", side_effect=OSError("fchmod failed")),
        pytest.raises(OSError, match="fchmod failed")
    ):
        mock_settings.get_data_dir.return_value = tmp_path
        asyncio.run(_save_folder_id("myfolder", "123"))

def test_gdrive_download_file_fchmod_propagates(tmp_path):
    import asyncio

    from mnemo_mcp.sync.gdrive import _download_file

    dest_path = tmp_path / "dest.bin"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"content"

    with (
        patch("mnemo_mcp.sync.gdrive._drive_request", return_value=mock_response),
        patch("os.name", "posix"),
        patch("os.fchmod", side_effect=OSError("fchmod failed")),
        pytest.raises(OSError, match="fchmod failed")
    ):
        asyncio.run(_download_file({}, "file_id", dest_path))

def test_server_write_secure_bytes_fchmod_propagates(tmp_path):
    import asyncio

    import mnemo_mcp.server
    from mnemo_mcp.db import MemoryDB

    mock_db = MagicMock(spec=MemoryDB)

    with (
        patch("mnemo_mcp.server.settings") as mock_settings,
        patch("mnemo_mcp.server.os.name", "posix"),
        patch("mnemo_mcp.server.os.fchmod", side_effect=OSError("fchmod failed")),
        patch("mnemo_mcp.server._get_ctx", return_value=(mock_db, None, None)),
        patch("mnemo_mcp.server._resolve_sync_passphrase", return_value="passphrase"),
        patch("mnemo_mcp.server.build_full_bundle", return_value=b"bundle_data", create=True),
        patch("mnemo_mcp.sync.delta.build_full_bundle", return_value=b"bundle_data"),
        pytest.raises(OSError, match="fchmod failed")
    ):
        mock_settings.get_data_dir.return_value = tmp_path
        asyncio.run(mnemo_mcp.server._handle_config_export_passport(None))
