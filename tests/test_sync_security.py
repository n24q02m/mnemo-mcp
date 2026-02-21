
import asyncio
import hashlib
import io
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mnemo_mcp.sync import _download_rclone, _RCLONE_VERSION


@pytest.fixture
def mock_platform_info():
    """Mock platform info to ensure consistent filename."""
    with patch("mnemo_mcp.sync._get_platform_info") as mock:
        mock.return_value = ("linux", "amd64", "")
        yield mock


@pytest.fixture
def fake_zip_content():
    """Create a valid zip file in memory containing a dummy 'rclone' binary."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("rclone-v1.68.2-linux-amd64/rclone", b"dummy_binary_content")
    return buffer.getvalue()


@pytest.fixture
def valid_checksum(fake_zip_content):
    """Calculate the correct SHA256 checksum for the fake zip."""
    return hashlib.sha256(fake_zip_content).hexdigest()


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient to handle multiple requests."""
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    # Store mocked responses
    mock_client._responses = {}

    async def get(url, timeout=None):
        if url in mock_client._responses:
            return mock_client._responses[url]
        else:
            # Default mock response if not found
            resp = MagicMock()
            resp.status_code = 404
            resp.raise_for_status.side_effect = Exception(f"404 Not Found: {url}")
            return resp

    mock_client.get = get
    return mock_client


@pytest.mark.asyncio
async def test_download_rclone_verification_success(
    tmp_path, mock_platform_info, fake_zip_content, valid_checksum, mock_httpx_client
):
    """Verify that _download_rclone succeeds when checksum matches."""

    zip_url = f"https://github.com/rclone/rclone/releases/download/{_RCLONE_VERSION}/rclone-{_RCLONE_VERSION}-linux-amd64.zip"
    sums_url = f"https://github.com/rclone/rclone/releases/download/{_RCLONE_VERSION}/SHA256SUMS"

    # Mock zip response
    zip_resp = MagicMock()
    zip_resp.status_code = 200
    zip_resp.content = fake_zip_content
    zip_resp.raise_for_status = MagicMock()

    # Mock sums response
    sums_resp = MagicMock()
    sums_resp.status_code = 200
    sums_resp.text = f"{valid_checksum}  rclone-{_RCLONE_VERSION}-linux-amd64.zip\n"
    sums_resp.raise_for_status = MagicMock()

    mock_httpx_client._responses[zip_url] = zip_resp
    mock_httpx_client._responses[sums_url] = sums_resp

    with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await _download_rclone()

            assert result is not None
            assert result.exists()
            assert result.read_bytes() == b"dummy_binary_content"


@pytest.mark.asyncio
async def test_download_rclone_verification_failure(
    tmp_path, mock_platform_info, fake_zip_content, mock_httpx_client
):
    """Verify that _download_rclone fails when checksum mismatches."""

    zip_url = f"https://github.com/rclone/rclone/releases/download/{_RCLONE_VERSION}/rclone-{_RCLONE_VERSION}-linux-amd64.zip"
    sums_url = f"https://github.com/rclone/rclone/releases/download/{_RCLONE_VERSION}/SHA256SUMS"

    # Mock zip response
    zip_resp = MagicMock()
    zip_resp.status_code = 200
    zip_resp.content = fake_zip_content
    zip_resp.raise_for_status = MagicMock()

    # Mock sums response with WRONG checksum
    wrong_checksum = "a" * 64
    sums_resp = MagicMock()
    sums_resp.status_code = 200
    sums_resp.text = f"{wrong_checksum}  rclone-{_RCLONE_VERSION}-linux-amd64.zip\n"
    sums_resp.raise_for_status = MagicMock()

    mock_httpx_client._responses[zip_url] = zip_resp
    mock_httpx_client._responses[sums_url] = sums_resp

    with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await _download_rclone()

            assert result is None  # Should return None on failure


@pytest.mark.asyncio
async def test_download_rclone_checksum_missing(
    tmp_path, mock_platform_info, fake_zip_content, mock_httpx_client
):
    """Verify that _download_rclone fails when filename is not in SHA256SUMS."""

    zip_url = f"https://github.com/rclone/rclone/releases/download/{_RCLONE_VERSION}/rclone-{_RCLONE_VERSION}-linux-amd64.zip"
    sums_url = f"https://github.com/rclone/rclone/releases/download/{_RCLONE_VERSION}/SHA256SUMS"

    # Mock zip response
    zip_resp = MagicMock()
    zip_resp.status_code = 200
    zip_resp.content = fake_zip_content
    zip_resp.raise_for_status = MagicMock()

    # Mock sums response with missing file
    sums_resp = MagicMock()
    sums_resp.status_code = 200
    sums_resp.text = f"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  other-file.zip\n"
    sums_resp.raise_for_status = MagicMock()

    mock_httpx_client._responses[zip_url] = zip_resp
    mock_httpx_client._responses[sums_url] = sums_resp

    with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await _download_rclone()

            assert result is None  # Should return None on failure
