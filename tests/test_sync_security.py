"""Tests for rclone download security verification."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.sync import _RCLONE_VERSION, _download_rclone, _verify_checksum


class TestChecksumVerification:
    def test_verify_checksum_valid(self):
        """Valid checksum matches content."""
        content = b"test content"
        sha256 = hashlib.sha256(content).hexdigest()
        filename = "test-file.zip"
        sums_text = f"{sha256}  {filename}\notherhash  otherfile.zip"

        assert _verify_checksum(content, filename, sums_text) is True

    def test_verify_checksum_invalid(self):
        """Invalid checksum fails verification."""
        content = b"test content"
        sha256 = "0" * 64  # Fake hash
        filename = "test-file.zip"
        sums_text = f"{sha256}  {filename}"

        assert _verify_checksum(content, filename, sums_text) is False

    def test_verify_checksum_missing_file(self):
        """Filename not in sums file returns False."""
        content = b"test content"
        filename = "test-file.zip"
        sums_text = "hash  otherfile.zip"

        assert _verify_checksum(content, filename, sums_text) is False

    def test_verify_checksum_malformed_sums(self):
        """Malformed sums file handles gracefully."""
        content = b"test content"
        filename = "test-file.zip"
        sums_text = "invalid line\n"

        assert _verify_checksum(content, filename, sums_text) is False


class TestDownloadSecurity:
    @pytest.fixture
    def mock_zipfile(self):
        with patch("mnemo_mcp.sync.zipfile.ZipFile") as mock:
            yield mock

    @pytest.fixture
    def mock_verify(self):
        with patch("mnemo_mcp.sync._verify_checksum") as mock:
            yield mock

    async def test_download_verifies_checksum(
        self, mock_zipfile, mock_verify, tmp_path
    ):
        """Download calls verify_checksum and succeeds if valid."""

        with patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_httpx:
            # Mock responses
            mock_client = AsyncMock()

            # Ensure async with works correctly
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            # Zip response
            zip_content = b"zip content"
            zip_response = MagicMock(name="ZipResponse")
            zip_response.content = zip_content

            # Sums response
            sums_content = "sums content"
            sums_response = MagicMock(name="SumsResponse")
            sums_response.text = sums_content

            # Sequential responses for get() calls
            mock_client.get.side_effect = [zip_response, sums_response]

            # Mock verification success
            mock_verify.return_value = True

            # Mock platform info to predict filename
            with patch(
                "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
            ):
                # Mock get_rclone_dir to use tmp_path
                with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
                    # Mock zip extraction
                    mock_zip = MagicMock()
                    mock_zipfile.return_value.__enter__.return_value = mock_zip
                    mock_zip.infolist.return_value = [
                        MagicMock(filename="rclone", is_dir=lambda: False)
                    ]

                    # Mock file read inside zip
                    mock_open_context = MagicMock()
                    mock_zip.open.return_value.__enter__.return_value = (
                        mock_open_context
                    )
                    mock_open_context.read.return_value = b"rclone binary content"

                    result = await _download_rclone()

                    assert result is not None
                    assert mock_verify.called
                    # Check arguments passed to verify
                    args = mock_verify.call_args
                    assert args[0][0] == zip_content
                    assert args[0][1] == f"rclone-{_RCLONE_VERSION}-linux-amd64.zip"
                    assert args[0][2] == sums_content

    async def test_download_fails_on_checksum_mismatch(
        self, mock_zipfile, mock_verify, tmp_path
    ):
        """Download returns None if verification fails."""

        with patch("mnemo_mcp.sync.httpx.AsyncClient") as mock_httpx:
            # Mock responses
            mock_client = AsyncMock()
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            mock_client.get.side_effect = [MagicMock(), MagicMock()]

            # Mock verification failure
            mock_verify.return_value = False

            with patch(
                "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
            ):
                with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
                    result = await _download_rclone()

                    assert result is None
                    # ZipFile should NOT be opened
                    assert not mock_zipfile.called
