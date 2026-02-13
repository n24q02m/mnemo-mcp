"""Tests for mnemo_mcp.sync — rclone management and sync operations."""

import pytest
import zipfile
import base64
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from mnemo_mcp.sync import (
    _extract_token,
    _get_platform_info,
    _prepare_rclone_env,
    setup_sync,
    sync_full,
)


class TestPlatformInfo:
    @patch("mnemo_mcp.sync.platform")
    def test_linux_amd64(self, mock_plat):
        mock_plat.system.return_value = "Linux"
        mock_plat.machine.return_value = "x86_64"
        os_name, arch, ext = _get_platform_info()
        assert os_name == "linux"
        assert arch == "amd64"
        assert ext == ""

    @patch("mnemo_mcp.sync.platform")
    def test_darwin_arm64(self, mock_plat):
        mock_plat.system.return_value = "Darwin"
        mock_plat.machine.return_value = "arm64"
        os_name, arch, ext = _get_platform_info()
        assert os_name == "osx"
        assert arch == "arm64"
        assert ext == ""

    @patch("mnemo_mcp.sync.platform")
    def test_windows(self, mock_plat):
        mock_plat.system.return_value = "Windows"
        mock_plat.machine.return_value = "AMD64"
        os_name, arch, ext = _get_platform_info()
        assert os_name == "windows"
        assert arch == "amd64"
        assert ext == ".exe"

    @patch("mnemo_mcp.sync.platform")
    def test_linux_arm64(self, mock_plat):
        mock_plat.system.return_value = "Linux"
        mock_plat.machine.return_value = "aarch64"
        os_name, arch, ext = _get_platform_info()
        assert os_name == "linux"
        assert arch == "arm64"

    @patch("mnemo_mcp.sync.platform")
    def test_unknown_arch_fallback(self, mock_plat):
        mock_plat.system.return_value = "Linux"
        mock_plat.machine.return_value = "riscv64"
        _, arch, _ = _get_platform_info()
        assert arch == "amd64"  # Fallback

    @patch("mnemo_mcp.sync.platform")
    def test_i686_maps_to_386(self, mock_plat):
        mock_plat.system.return_value = "Linux"
        mock_plat.machine.return_value = "i686"
        _, arch, _ = _get_platform_info()
        assert arch == "386"


class TestSyncFull:
    async def test_disabled(self, tmp_db):
        """Sync returns disabled when not configured."""
        with patch("mnemo_mcp.sync.settings") as mock_settings:
            mock_settings.sync_enabled = False
            mock_settings.sync_remote = ""
            result = await sync_full(tmp_db)
            assert result["status"] == "disabled"

    async def test_no_rclone(self, tmp_db):
        """Sync errors when rclone is not available."""
        with (
            patch("mnemo_mcp.sync.settings") as mock_settings,
            patch(
                "mnemo_mcp.sync.ensure_rclone",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_settings.sync_enabled = True
            mock_settings.sync_remote = "test-remote"
            result = await sync_full(tmp_db)
            assert result["status"] == "error"
            assert "rclone" in result["message"].lower()

    async def test_remote_not_configured(self, tmp_db, tmp_path):
        """Sync errors when rclone remote is not set up."""
        rclone_path = tmp_path / "rclone"
        rclone_path.touch()
        with (
            patch("mnemo_mcp.sync.settings") as mock_settings,
            patch(
                "mnemo_mcp.sync.ensure_rclone",
                new_callable=AsyncMock,
                return_value=rclone_path,
            ),
            patch(
                "mnemo_mcp.sync.check_remote_configured",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            mock_settings.sync_enabled = True
            mock_settings.sync_remote = "gdrive"
            result = await sync_full(tmp_db)
            assert result["status"] == "error"
            assert "gdrive" in result["message"]
            assert "RCLONE_CONFIG_GDRIVE_TYPE" in result["message"]


class TestExtractToken:
    def test_between_dashes(self):
        output = (
            "Paste the following into your remote machine config\n"
            "--------------------\n"
            '{"access_token":"ya29.abc","token_type":"Bearer"}\n'
            "--------------------\n"
        )
        token = _extract_token(output)
        assert token is not None
        assert '"access_token"' in token

    def test_fallback_access_token(self):
        output = 'Some text {"access_token":"ya29.abc","token_type":"Bearer"} more text'
        token = _extract_token(output)
        assert token is not None
        assert '"access_token"' in token

    def test_no_token(self):
        assert _extract_token("no token here") is None

    def test_empty(self):
        assert _extract_token("") is None


class TestPrepareRcloneEnv:
    def test_decode_base64_token(self):
        """Base64-encoded token is decoded for rclone."""
        token = json.dumps({"access_token": "ya29.abc", "token_type": "Bearer"})
        b64 = base64.b64encode(token.encode()).decode()
        with patch.dict(os.environ, {"RCLONE_CONFIG_GDRIVE_TOKEN": b64}):
            env = _prepare_rclone_env()
            assert env["RCLONE_CONFIG_GDRIVE_TOKEN"] == token

    def test_raw_json_passthrough(self):
        """Raw JSON token is passed through unchanged."""
        token = '{"access_token": "ya29.abc", "token_type": "Bearer"}'
        with patch.dict(os.environ, {"RCLONE_CONFIG_GDRIVE_TOKEN": token}):
            env = _prepare_rclone_env()
            assert env["RCLONE_CONFIG_GDRIVE_TOKEN"] == token

    def test_invalid_base64_passthrough(self):
        """Invalid base64 value is left unchanged."""
        with patch.dict(os.environ, {"RCLONE_CONFIG_GDRIVE_TOKEN": "not-valid!!!"}):
            env = _prepare_rclone_env()
            assert env["RCLONE_CONFIG_GDRIVE_TOKEN"] == "not-valid!!!"

    def test_non_token_vars_unchanged(self):
        """Non-TOKEN rclone config vars are not modified."""
        with patch.dict(os.environ, {"RCLONE_CONFIG_GDRIVE_TYPE": "drive"}):
            env = _prepare_rclone_env()
            assert env["RCLONE_CONFIG_GDRIVE_TYPE"] == "drive"


class TestSetupSync:
    def _mock_result(self, returncode: int = 0, stdout: str = ""):
        return MagicMock(returncode=returncode, stdout=stdout)

    def test_rclone_found(self, tmp_path, capsys):
        """setup_sync uses existing rclone and runs authorize."""
        rclone_path = tmp_path / "rclone"
        rclone_path.touch()
        with (
            patch("mnemo_mcp.sync._get_rclone_path", return_value=rclone_path),
            patch(
                "mnemo_mcp.sync.subprocess.run",
                return_value=self._mock_result(),
            ) as mock_run,
        ):
            setup_sync("drive")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == [str(rclone_path), "authorize", "drive"]

    def test_rclone_downloaded(self, tmp_path, capsys):
        """setup_sync downloads rclone when not found."""
        rclone_path = tmp_path / "rclone"
        with (
            patch("mnemo_mcp.sync._get_rclone_path", return_value=None),
            patch("mnemo_mcp.sync.asyncio.run", return_value=rclone_path),
            patch(
                "mnemo_mcp.sync.subprocess.run",
                return_value=self._mock_result(),
            ),
        ):
            setup_sync("drive")
            captured = capsys.readouterr()
            assert "Downloading rclone" in captured.out

    def test_download_fails(self, capsys):
        """setup_sync exits when rclone download fails."""
        with (
            patch("mnemo_mcp.sync._get_rclone_path", return_value=None),
            patch("mnemo_mcp.sync.asyncio.run", return_value=None),
        ):
            import pytest

            with pytest.raises(SystemExit, match="1"):
                setup_sync("drive")

    def test_authorize_fails(self, tmp_path):
        """setup_sync exits when rclone authorize fails."""
        rclone_path = tmp_path / "rclone"
        rclone_path.touch()
        with (
            patch("mnemo_mcp.sync._get_rclone_path", return_value=rclone_path),
            patch(
                "mnemo_mcp.sync.subprocess.run",
                return_value=self._mock_result(returncode=1),
            ),
        ):
            import pytest

            with pytest.raises(SystemExit, match="1"):
                setup_sync("drive")

    def test_fallback_instructions(self, tmp_path, capsys):
        """setup_sync shows manual instructions when token not extracted."""
        rclone_path = tmp_path / "rclone"
        rclone_path.touch()
        with (
            patch("mnemo_mcp.sync._get_rclone_path", return_value=rclone_path),
            patch(
                "mnemo_mcp.sync.subprocess.run",
                return_value=self._mock_result(stdout="no token here"),
            ),
        ):
            setup_sync("s3")
            captured = capsys.readouterr()
            assert "MANUAL SETUP" in captured.out
            assert "base64" in captured.out.lower()
            assert "RCLONE_CONFIG_S3_TYPE" in captured.out

    def test_auto_extract_token(self, tmp_path, capsys):
        """setup_sync outputs base64 token value for copy-paste."""
        rclone_path = tmp_path / "rclone"
        rclone_path.touch()
        token_json = '{"access_token":"ya29.abc","token_type":"Bearer"}'
        token_output = f"--------------------\n{token_json}\n--------------------\n"
        expected_b64 = base64.b64encode(token_json.encode()).decode()
        with (
            patch("mnemo_mcp.sync._get_rclone_path", return_value=rclone_path),
            patch(
                "mnemo_mcp.sync.subprocess.run",
                return_value=self._mock_result(stdout=token_output),
            ),
        ):
            setup_sync("drive")
            captured = capsys.readouterr()
            assert "RCLONE_CONFIG_GDRIVE_TOKEN" in captured.out
            assert expected_b64 in captured.out
            assert "SYNC_ENABLED=true" in captured.out
            assert "auto-decodes base64" in captured.out


class TestDownloadHelpers:
    def test_get_download_url(self):
        from mnemo_mcp.sync import _get_download_url

        url = _get_download_url("v1.0.0", "linux", "amd64")
        assert (
            url
            == "https://github.com/rclone/rclone/releases/download/v1.0.0/rclone-v1.0.0-linux-amd64.zip"
        )

    @pytest.mark.asyncio
    async def test_download_file_success(self, tmp_path):
        from mnemo_mcp.sync import _download_file

        # Mock httpx.AsyncClient
        with patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b"fake-zip-content"
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response

            path = await _download_file("http://example.com/file.zip")

            assert path.exists()
            assert path.read_bytes() == b"fake-zip-content"
            path.unlink()

    def test_extract_binary_success(self, tmp_path):
        from mnemo_mcp.sync import _extract_binary_from_zip

        zip_path = tmp_path / "test.zip"
        target_path = tmp_path / "extracted_binary"

        # Create a valid zip file
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("folder/binary", b"binary-content")

        assert _extract_binary_from_zip(zip_path, "binary", target_path)
        assert target_path.exists()
        assert target_path.read_bytes() == b"binary-content"

    def test_extract_binary_not_found(self, tmp_path):
        from mnemo_mcp.sync import _extract_binary_from_zip

        zip_path = tmp_path / "test.zip"
        target_path = tmp_path / "extracted_binary"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("folder/other", b"content")

        assert not _extract_binary_from_zip(zip_path, "binary", target_path)
        assert not target_path.exists()
