from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mnemo_mcp.sync import sync_pull


class TestSyncPull:
    @pytest.fixture
    def mock_run_rclone(self):
        with patch("mnemo_mcp.sync._run_rclone") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_pull_success(self, tmp_path, mock_run_rclone):
        """Test successful pull where rclone succeeds and file exists."""
        # Setup
        rclone_path = Path("/usr/bin/rclone")
        db_path = tmp_path / "data" / "memory.db"
        # Ensure parent dir exists (sync_pull will do mkdir parents=True on sync_temp, so parent of db_path is implicit)
        # But db_path.parent usually exists in real usage.

        remote = "gdrive"
        folder = "mnemo_backup"

        # Calculate expected temp path
        temp_dir = db_path.parent / "sync_temp"
        expected_temp_db = temp_dir / f"remote_{db_path.name}"

        # Side effect to create the file when rclone is called
        def create_file(*args, **kwargs):
            # Create parent dir if not exists (sync_pull does this before calling rclone, so it should exist)
            # But let's be safe in mock
            expected_temp_db.parent.mkdir(parents=True, exist_ok=True)
            expected_temp_db.touch()
            return MagicMock(returncode=0)

        mock_run_rclone.side_effect = create_file

        # Execute
        result = await sync_pull(rclone_path, db_path, remote, folder)

        # Verify
        assert result == expected_temp_db
        assert result.exists()

        mock_run_rclone.assert_called_once()
        args = mock_run_rclone.call_args
        # args[0] is (rclone_path, [cmd_list], timeout)
        assert args[0][0] == rclone_path
        cmd_list = args[0][1]
        assert cmd_list[0] == "copyto"
        # Remote source path
        assert cmd_list[1] == f"{remote}:{folder}/{db_path.name}"
        # Local destination path
        assert cmd_list[2] == str(expected_temp_db)

    @pytest.mark.asyncio
    async def test_pull_failure_rclone_error(self, tmp_path, mock_run_rclone):
        """Test failure when rclone command fails."""
        # Setup
        rclone_path = Path("/usr/bin/rclone")
        db_path = tmp_path / "data" / "memory.db"
        remote = "gdrive"
        folder = "mnemo_backup"

        mock_run_rclone.return_value = MagicMock(returncode=1, stderr="error")

        # Execute
        result = await sync_pull(rclone_path, db_path, remote, folder)

        # Verify
        assert result is None
        mock_run_rclone.assert_called_once()

    @pytest.mark.asyncio
    async def test_pull_failure_no_file(self, tmp_path, mock_run_rclone):
        """Test failure when rclone succeeds but file is missing."""
        # Setup
        rclone_path = Path("/usr/bin/rclone")
        db_path = tmp_path / "data" / "memory.db"
        remote = "gdrive"
        folder = "mnemo_backup"

        # Mock success (returncode 0) but do NOT create the file
        mock_run_rclone.return_value = MagicMock(returncode=0)

        # Execute
        result = await sync_pull(rclone_path, db_path, remote, folder)

        # Verify
        assert result is None
        mock_run_rclone.assert_called_once()
