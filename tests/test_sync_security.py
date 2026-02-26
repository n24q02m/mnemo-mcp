
import asyncio
import hashlib
import stat
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from mnemo_mcp.sync import _download_rclone, _get_platform_info

# Helper to generate a fake zip file content
def create_fake_zip(filename: str, content: bytes) -> bytes:
    import io
    import zipfile

    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as zf:
        zf.writestr(filename, content)
    return b.getvalue()

@pytest.mark.asyncio
async def test_download_rclone_checksum_verification_success():
    """Test that download succeeds when checksum matches."""
    os_name, arch, ext = _get_platform_info()
    platform_key = f"{os_name}-{arch}"

    fake_content = b"fake-rclone-binary"
    fake_zip_content = create_fake_zip(f"rclone{ext}", fake_content)
    sha256 = hashlib.sha256(fake_zip_content).hexdigest()

    mock_checksums = {platform_key: sha256}

    with patch("mnemo_mcp.sync._RCLONE_CHECKSUMS", mock_checksums, create=True), \
         patch("httpx.AsyncClient") as MockClient, \
         patch("pathlib.Path.write_bytes"), \
         patch("pathlib.Path.chmod"), \
         patch("pathlib.Path.stat") as mock_stat, \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("tempfile.NamedTemporaryFile") as mock_temp:

        # Ensure it attempts download
        mock_exists.return_value = False

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = fake_zip_content
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        # Mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/fake_rclone.zip"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        # Mock stat
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mode = stat.S_IRUSR
        mock_stat.return_value = mock_stat_obj

        with patch("zipfile.ZipFile") as MockZip:
             mock_zip_instance = MagicMock()
             mock_info = MagicMock()
             mock_info.filename = f"rclone-v1.68.2/{f'rclone{ext}'}"
             mock_info.is_dir.return_value = False

             mock_zip_instance.infolist.return_value = [mock_info]

             mock_src_file = MagicMock()
             mock_src_file.read.return_value = fake_content
             mock_zip_instance.open.return_value.__enter__.return_value = mock_src_file

             MockZip.return_value.__enter__.return_value = mock_zip_instance

             # RUN
             result = await _download_rclone()

             assert result is not None
             assert result.name == f"rclone{ext}"

@pytest.mark.asyncio
async def test_download_rclone_checksum_verification_failure():
    """Test that download fails when checksum does not match."""
    os_name, arch, ext = _get_platform_info()
    platform_key = f"{os_name}-{arch}"

    fake_content = b"fake-rclone-binary"
    fake_zip_content = create_fake_zip(f"rclone{ext}", fake_content)

    # WRONG CHECKSUM
    wrong_checksum = "0" * 64

    mock_checksums = {platform_key: wrong_checksum}

    with patch("mnemo_mcp.sync._RCLONE_CHECKSUMS", mock_checksums, create=True), \
         patch("httpx.AsyncClient") as MockClient, \
         patch("pathlib.Path.write_bytes"), \
         patch("pathlib.Path.chmod"), \
         patch("pathlib.Path.stat") as mock_stat, \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.exists") as mock_exists, \
         patch("tempfile.NamedTemporaryFile") as mock_temp:

        # Ensure it attempts download
        mock_exists.return_value = False

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.content = fake_zip_content
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        MockClient.return_value.__aenter__.return_value = mock_client_instance

        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/fake_rclone.zip"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        # Mock stat
        mock_stat.return_value.st_mode = stat.S_IRUSR

        with patch("zipfile.ZipFile") as MockZip:
             mock_zip_instance = MagicMock()
             MockZip.return_value.__enter__.return_value = mock_zip_instance

             # RUN
             result = await _download_rclone()

             assert result is None
