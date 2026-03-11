from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mnemo_mcp.sync import _download_rclone


@pytest.mark.asyncio
async def test_download_rclone_uses_configured_version(tmp_path):
    """Test that _download_rclone uses the version from settings."""
    # Mock settings
    with patch("mnemo_mcp.sync.settings") as mock_settings:
        mock_settings.rclone_version = "v1.99.9"

        # Mock platform info to get predictable URL
        with patch(
            "mnemo_mcp.sync._get_platform_info", return_value=("linux", "amd64", "")
        ):
            # Mock get_rclone_dir to return a temp dir
            with patch("mnemo_mcp.sync._get_rclone_dir", return_value=tmp_path):
                # Mock httpx.AsyncClient
                mock_client = AsyncMock()
                mock_checksums_response = MagicMock()
                mock_checksums_response.text = (
                    "1234567890abcdef  rclone-v1.99.9-linux-amd64.zip\n"
                )
                mock_zip_response = MagicMock()
                mock_zip_response.content = b"fake-zip-content"

                mock_client.get.side_effect = [
                    mock_checksums_response,
                    mock_zip_response,
                ]
                mock_client.__aenter__.return_value = mock_client

                with patch(
                    "mnemo_mcp.sync.httpx.AsyncClient", return_value=mock_client
                ):
                    # Mock zipfile to prevent errors
                    with patch("mnemo_mcp.sync.zipfile.ZipFile"):
                        # Mock tempfile to avoid writing
                        with patch(
                            "mnemo_mcp.sync.tempfile.NamedTemporaryFile"
                        ) as mock_temp:
                            mock_temp.return_value.__enter__.return_value.name = str(
                                tmp_path / "temp.zip"
                            )

                            # Mock hash mismatch to prevent extraction error
                            with patch("mnemo_mcp.sync.hashlib.sha256") as mock_sha256:
                                mock_sha256.return_value.hexdigest.return_value = (
                                    "1234567890abcdef"
                                )

                                # Need to mock the extraction to return True so we don't return None early
                                with patch(
                                    "mnemo_mcp.sync.asyncio.to_thread",
                                    return_value=True,
                                ):
                                    # Also mock open so hashlib reading works
                                    with patch(
                                        "builtins.open", new_callable=MagicMock
                                    ) as mock_open:
                                        mock_open.return_value.__enter__.return_value.read.side_effect = [
                                            b"data",
                                            b"",
                                        ]
                                        with patch("pathlib.Path.unlink"):
                                            with patch("pathlib.Path.chmod"):
                                                await _download_rclone()

                            # Verify both URLs were fetched
                            expected_checksums_url = "https://github.com/rclone/rclone/releases/download/v1.99.9/SHA256SUMS"
                            expected_zip_url = "https://github.com/rclone/rclone/releases/download/v1.99.9/rclone-v1.99.9-linux-amd64.zip"

                            mock_client.get.assert_any_call(
                                expected_checksums_url, timeout=30.0
                            )
                            mock_client.get.assert_any_call(
                                expected_zip_url, timeout=120.0
                            )
