"""Tests for mnemo_mcp.sync — rclone management and sync operations."""

import base64
import io
import json
import os
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

from mnemo_mcp.sync import (
    _download_rclone,
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


class TestDownloadRclone:
    async def test_download_success(self, tmp_path):
        """rclone binary is downloaded and extracted."""
        # 1. Prepare Zip Content
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Add binary file (simulate structure inside zip)
            # The code searches for file ending in 'rclone'/'rclone.exe'
            zf.writestr("rclone-v1.68.2-linux-amd64/rclone", b"dummy binary content")
        zip_content = zip_buffer.getvalue()

        # 2. Mock dependencies
        with (
            patch(
                "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
            ),
            patch("mnemo_mcp.sync.settings") as mock_settings,
            patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls,
        ):
            # Mock settings.get_data_dir to return tmp_path
            mock_settings.get_data_dir.return_value = tmp_path

            # Mock httpx response
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.content = zip_content

            # Mock client context manager
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # 3. Run
            result = await _download_rclone()

            # 4. Verify
            expected_path = tmp_path / "bin" / "rclone"
            assert result == expected_path
            assert expected_path.exists()
            assert expected_path.read_bytes() == b"dummy binary content"

            # Verify chmod (executable permission)
            if os.name != "nt":
                assert os.access(expected_path, os.X_OK)

    async def test_already_exists(self, tmp_path):
        """Returns early if rclone binary already exists."""
        # 1. Setup
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(parents=True)
        rclone_path = bin_dir / "rclone"
        rclone_path.write_bytes(b"existing binary")

        # 2. Mock
        with (
            patch(
                "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
            ),
            patch("mnemo_mcp.sync.settings") as mock_settings,
            patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.get_data_dir.return_value = tmp_path

            # 3. Run
            result = await _download_rclone()

            # 4. Verify
            assert result == rclone_path
            mock_client_cls.assert_not_called()

    async def test_download_failure(self, tmp_path):
        """Returns None if download fails."""
        with (
            patch(
                "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
            ),
            patch("mnemo_mcp.sync.settings") as mock_settings,
            patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.get_data_dir.return_value = tmp_path

            # Mock exception
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Download error")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _download_rclone()

            assert result is None

    async def test_extraction_failure(self, tmp_path):
        """Returns None if zip does not contain rclone binary."""
        # 1. Prepare Zip Content (no binary)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("readme.txt", b"instructions")
        zip_content = zip_buffer.getvalue()

        # 2. Mock
        with (
            patch(
                "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
            ),
            patch("mnemo_mcp.sync.settings") as mock_settings,
            patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.get_data_dir.return_value = tmp_path

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.content = zip_content

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # 3. Run
            result = await _download_rclone()

            # 4. Verify
            assert result is None
