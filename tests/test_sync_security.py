
import hashlib
import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mnemo_mcp.sync import _download_rclone, _RCLONE_VERSION

# Helper to create a dummy zip with a file inside
def create_zip_bytes(filename: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    return buf.getvalue()

@pytest.mark.asyncio
async def test_download_rclone_verification_failure(tmp_path):
    """Test that _download_rclone fails if SHA256SUMS hash does not match."""

    # Fake rclone binary
    mock_rclone_binary = b"fake-rclone-binary"

    # Mock platform info to get a predictable zip filename
    with patch("mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")):
        zip_filename = f"rclone-{_RCLONE_VERSION}-linux-amd64.zip"

        # Create a zip containing the binary
        zip_bytes = create_zip_bytes("rclone-v1.2.3-linux-amd64/rclone", mock_rclone_binary)

        # Calculate real hash so we can give a WRONG one in SHA256SUMS
        real_hash = hashlib.sha256(zip_bytes).hexdigest()
        fake_hash = "0" * 64  # Clearly wrong hash

        # Mock SHA256SUMS content
        sums_content = f"{fake_hash}  {zip_filename}\n"

        # Mock httpx response objects
        mock_response_zip = MagicMock()
        mock_response_zip.content = zip_bytes
        mock_response_zip.raise_for_status = MagicMock()

        mock_response_sums = MagicMock()
        mock_response_sums.text = sums_content
        mock_response_sums.raise_for_status = MagicMock()

        # Side effect for client.get
        async def side_effect(url, **kwargs):
            if url.endswith(".zip"):
                return mock_response_zip
            elif url.endswith("SHA256SUMS"):
                return mock_response_sums
            raise ValueError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get.side_effect = side_effect

        mock_client_cls = MagicMock()
        mock_client_cls.__aenter__.return_value = mock_client
        mock_client_cls.__aexit__.return_value = None

        with patch("mnemo_mcp.sync.httpx.AsyncClient", return_value=mock_client_cls):
            with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
                result = await _download_rclone()
                assert result is None

@pytest.mark.asyncio
async def test_download_rclone_verification_success(tmp_path):
    """Test that _download_rclone succeeds if SHA256SUMS hash matches."""

    mock_rclone_binary = b"fake-rclone-binary"

    with patch("mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")):
        zip_filename = f"rclone-{_RCLONE_VERSION}-linux-amd64.zip"

        zip_bytes = create_zip_bytes("rclone-v1.2.3-linux-amd64/rclone", mock_rclone_binary)

        real_hash = hashlib.sha256(zip_bytes).hexdigest()

        sums_content = f"{real_hash}  {zip_filename}\n"

        mock_response_zip = MagicMock()
        mock_response_zip.content = zip_bytes
        mock_response_zip.raise_for_status = MagicMock()

        mock_response_sums = MagicMock()
        mock_response_sums.text = sums_content
        mock_response_sums.raise_for_status = MagicMock()

        async def side_effect(url, **kwargs):
            if url.endswith(".zip"):
                return mock_response_zip
            elif url.endswith("SHA256SUMS"):
                return mock_response_sums
            raise ValueError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get.side_effect = side_effect

        mock_client_cls = MagicMock()
        mock_client_cls.__aenter__.return_value = mock_client
        mock_client_cls.__aexit__.return_value = None

        with patch("mnemo_mcp.sync.httpx.AsyncClient", return_value=mock_client_cls):
            with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
                # Also need to mock chmod since it might be called on linux
                with patch("pathlib.Path.chmod"):
                    result = await _download_rclone()
                    assert result is not None
                    assert result.exists()
                    assert result.read_bytes() == mock_rclone_binary
