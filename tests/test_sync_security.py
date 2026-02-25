import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.sync import _download_rclone


@pytest.mark.asyncio
async def test_download_rclone_checksum_verification_fail():
    """Test that download fails when checksum mismatches."""

    fake_hash = "a" * 64
    content = b"malicious content"

    with (
        patch("mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")),
        patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls,
        patch("mnemo_mcp.sync.zipfile.ZipFile") as mock_zip_cls,
        patch(
            "mnemo_mcp.sync._RCLONE_CHECKSUMS", {"linux-amd64": fake_hash}, create=True
        ),
        patch("pathlib.Path.write_bytes"),
        patch("pathlib.Path.exists", return_value=False),
        patch("mnemo_mcp.sync.tempfile.NamedTemporaryFile") as mock_temp_cls,
        patch("pathlib.Path.chmod"),
        patch("pathlib.Path.stat") as mock_stat,
        patch("pathlib.Path.mkdir"),
    ):
        # Mock client
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp_cls.return_value.__enter__.return_value = mock_temp
        mock_temp.name = "/tmp/fake.zip"

        # Mock zip extraction (make it succeed finding the binary)
        mock_zip = MagicMock()
        mock_zip_cls.return_value.__enter__.return_value = mock_zip

        mock_zip_info = MagicMock()
        mock_zip_info.filename = "rclone"
        mock_zip_info.is_dir.return_value = False
        mock_zip.infolist.return_value = [mock_zip_info]

        mock_zip_open = MagicMock()
        mock_zip_open.read.return_value = b"binary content"
        mock_zip.open.return_value.__enter__.return_value = mock_zip_open

        # Mock stat for chmod
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644
        mock_stat.return_value = mock_stat_result

        # Execute
        result = await _download_rclone()

        # Assertions
        assert result is None, "Should return None on checksum mismatch"


@pytest.mark.asyncio
async def test_download_rclone_checksum_verification_success():
    """Test that download succeeds when checksum matches."""
    content = b"valid content"
    expected_hash = hashlib.sha256(content).hexdigest()

    with (
        patch("mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")),
        patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_client_cls,
        patch("mnemo_mcp.sync.zipfile.ZipFile") as mock_zip_cls,
        patch(
            "mnemo_mcp.sync._RCLONE_CHECKSUMS",
            {"linux-amd64": expected_hash},
            create=True,
        ),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.exists", return_value=False),
        patch("mnemo_mcp.sync.tempfile.NamedTemporaryFile") as mock_temp_cls,
        patch("pathlib.Path.chmod"),
        patch("pathlib.Path.write_bytes"),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # Mock client
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp_cls.return_value.__enter__.return_value = mock_temp
        mock_temp.name = "/tmp/fake.zip"

        # Mock zip extraction
        mock_zip = MagicMock()
        mock_zip_cls.return_value.__enter__.return_value = mock_zip

        # Mock zip info
        mock_zip_info = MagicMock()
        mock_zip_info.filename = "rclone"
        mock_zip_info.is_dir.return_value = False
        mock_zip.infolist.return_value = [mock_zip_info]

        # Mock zip open
        mock_zip_open = MagicMock()
        mock_zip_open.read.return_value = b"binary content"
        mock_zip.open.return_value.__enter__.return_value = mock_zip_open

        # Mock stat for chmod
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644
        mock_stat.return_value = mock_stat_result

        # Execute
        result = await _download_rclone()

        # Assertions
        assert result is not None
        assert result.name == "rclone"
