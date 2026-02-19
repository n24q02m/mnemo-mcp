"""Security tests for configuration validation."""

import pytest
from pydantic import ValidationError

from mnemo_mcp.config import Settings


class TestSecurityConfig:
    def test_sync_remote_injection(self):
        """Ensure sync_remote cannot start with '-' to prevent argument injection."""
        with pytest.raises(ValidationError) as exc:
            Settings(sync_remote="-bad-remote")
        assert "sync_remote" in str(exc.value)

    def test_sync_remote_special_chars(self):
        """Ensure sync_remote only contains alphanumeric chars, dashes, underscores, and dots."""
        invalid_remotes = [
            "remote; rm -rf /",
            "remote | bash",
            "remote&",
            "remote$(whoami)",
        ]
        for remote in invalid_remotes:
            with pytest.raises(ValidationError) as exc:
                Settings(sync_remote=remote)
            assert "sync_remote" in str(exc.value)

    def test_sync_remote_valid(self):
        """Ensure valid remotes are accepted."""
        valid_remotes = [
            "gdrive",
            "my-remote",
            "my_remote",
            "remote.1",
            "USER_backup",
        ]
        for remote in valid_remotes:
            s = Settings(sync_remote=remote)
            assert s.sync_remote == remote

    def test_sync_folder_traversal(self):
        """Ensure sync_folder cannot contain traversal sequences."""
        invalid_folders = [
            "../parent",
            "folder/../parent",
            "..",
            "/absolute/path",  # Should also reject absolute paths
        ]
        for folder in invalid_folders:
            with pytest.raises(ValidationError) as exc:
                Settings(sync_folder=folder)
            assert "sync_folder" in str(exc.value)

    def test_sync_folder_valid(self):
        """Ensure valid folders are accepted."""
        valid_folders = [
            "mnemo-mcp",
            "sub/folder",
            "data_2024",
        ]
        for folder in valid_folders:
            s = Settings(sync_folder=folder)
            assert s.sync_folder == folder
