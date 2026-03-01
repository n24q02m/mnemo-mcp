"""Security tests for rclone download verification."""

import hashlib
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.sync import _download_rclone


@pytest.fixture
def mock_platform():
    with patch("mnemo_mcp.sync._get_platform_info") as mock:
        # Simulate linux-amd64 which we have a checksum for
        mock.return_value = ("linux", "amd64", "")
        yield mock


@pytest.fixture
def mock_rclone_dir(tmp_path):
    with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def fake_zip_content():
    """Create a minimal valid zip file content."""
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("rclone", b"fake binary content")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_download_verification_failure(
    mock_platform, mock_rclone_dir, fake_zip_content
):
    """Test that download fails when checksum does not match."""
    # The current implementation (vulnerable) will download this successfully.
    # The fixed implementation should return None because the checksum won't match
    # the real rclone checksum hardcoded in the source.

    # We mock httpx to return our fake zip
    mock_response = MagicMock()
    mock_response.content = fake_zip_content
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        # We also need to mock zipfile extraction to avoid actually writing files
        # or just let it write to tmp_path which is fine.
        # But wait, the code extracts 'rclone' from the zip.
        # Our fake zip has 'rclone' inside, so extraction should work.

        result = await _download_rclone()

    # Vulnerability check:
    # IF vulnerable: result is not None (it returns the path)
    # IF fixed: result is None (checksum mismatch)

    # We assert what we EXPECT after the fix.
    # So this test will FAIL until I apply the fix.
    assert result is None


@pytest.mark.asyncio
async def test_download_verification_success(mock_platform, mock_rclone_dir):
    """Test that download succeeds when checksum matches."""
    # This is trickier because we need to match the REAL checksum in the source code.
    # We can patch the _RCLONE_CHECKSUMS dict in the source if we want to test logic,
    # or we can compute the hash of our fake zip and put it in the dict.

    # Create a valid zip structure
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("rclone", b"binary")
    zip_bytes = buffer.getvalue()

    expected_hash = hashlib.sha256(zip_bytes).hexdigest()

    mock_response = MagicMock()
    mock_response.content = zip_bytes

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client

    # We need to patch the checksum dict in the module
    # But first we need to make sure the module has it (it doesn't yet).
    # So for now, we can't write this test fully correctly without the fix code existing.
    # But we can write it using patch.dict on the module's dictionary ONCE IT EXISTS.

    # For now, I'll just write the test assuming the dict exists,
    # knowing it will error out until I add the dict.

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "mnemo_mcp.sync._RCLONE_CHECKSUMS",
            {"linux-amd64": expected_hash},
            create=True,
        ):
            result = await _download_rclone()

    assert result is not None
    assert result.name == "rclone"
