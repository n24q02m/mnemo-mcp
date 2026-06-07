import json
import os
import stat
from pathlib import Path
from unittest.mock import patch
import pytest

@pytest.fixture
def data_dir(tmp_path):
    with patch("mnemo_mcp.token_store.settings") as mock_settings:
        mock_settings.get_data_dir.return_value = tmp_path
        yield tmp_path

class TestTokenStoreCoverageExtra:
    def test_load_token_exists_oserror(self, data_dir):
        from mnemo_mcp.token_store import load_token

        with patch.object(Path, "exists", side_effect=OSError("exists error")):
            assert load_token("drive") is None

    def test_load_token_for_sub_exists_oserror(self, data_dir):
        from mnemo_mcp.token_store import load_token_for_sub

        with patch.object(Path, "exists", side_effect=OSError("exists error")):
            assert load_token_for_sub("user", "drive") is None

    def test_save_token_for_sub_fallback_chmod_oserror(self, data_dir):
        if os.name == "nt":
            pytest.skip("POSIX-only branch")
        from mnemo_mcp.token_store import save_token_for_sub

        with patch("mnemo_mcp.token_store.os.open", side_effect=OSError("open fail")):
            with patch.object(Path, "chmod", side_effect=OSError("chmod fail")):
                # Should not raise
                save_token_for_sub("user", "drive", {"access_token": "ok"})

        # Verify it still saved despite chmod failing
        from mnemo_mcp.token_store import get_token_path_for_sub
        path = get_token_path_for_sub("user", "drive")
        assert path.exists()
        assert json.loads(path.read_text())["access_token"] == "ok"

    def test_save_token_fallback_chmod_oserror_redundant(self, data_dir):
        """Redundant check for save_token (non-sub) fallback chmod error."""
        if os.name == "nt":
            pytest.skip("POSIX-only branch")
        from mnemo_mcp.token_store import save_token

        with patch("mnemo_mcp.token_store.os.open", side_effect=OSError("open fail")):
            with patch.object(Path, "chmod", side_effect=OSError("chmod fail")):
                save_token("drive", {"access_token": "ok"})

        from mnemo_mcp.token_store import get_token_path
        path = get_token_path("drive")
        assert path.exists()
