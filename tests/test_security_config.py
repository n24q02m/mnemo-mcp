"""Tests for security-related configuration validation."""

import pytest
from pydantic import ValidationError

from mnemo_mcp.config import Settings


class TestSecurityConfig:
    def test_sync_remote_validation(self):
        """Test validation for sync_remote."""
        s = Settings()

        # Valid values
        s.sync_remote = "gdrive"
        s.sync_remote = "my-remote"
        s.sync_remote = "remote_1"
        s.sync_remote = "user.name"

        # Invalid values
        with pytest.raises(ValidationError) as exc:
            s.sync_remote = "-gdrive"
        assert "Remote name cannot start with '-'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            s.sync_remote = "gdrive; rm -rf /"
        assert "Remote name must contain only" in str(exc.value)

    def test_sync_folder_validation(self):
        """Test validation for sync_folder."""
        s = Settings()

        # Valid values
        s.sync_folder = "mnemo"
        s.sync_folder = "path/to/folder"
        s.sync_folder = "my-folder_123"

        # Invalid values
        with pytest.raises(ValidationError) as exc:
            s.sync_folder = "/etc/passwd"
        assert "Folder must be a relative path" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            s.sync_folder = "../root"
        assert "Folder path cannot contain '..' segments" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            s.sync_folder = "-folder"
        assert "Folder name cannot start with '-'" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            s.sync_folder = "folder/../../root"
        assert "Folder path cannot contain '..' segments" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            s.sync_folder = "folder|pipe"
        assert "Folder path must contain only" in str(exc.value)

    def test_init_validation(self):
        """Test validation during initialization."""
        with pytest.raises(ValidationError):
            Settings(sync_remote="-bad")

        with pytest.raises(ValidationError):
            Settings(sync_folder="/bad")
