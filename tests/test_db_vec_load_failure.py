"""Tests for sqlite-vec load failure handling in MemoryDB."""

from unittest.mock import patch
from mnemo_mcp.db import MemoryDB

def test_sqlite_vec_load_failure_handled_gracefully(tmp_path):
    """Verify that MemoryDB handles sqlite-vec load failure gracefully."""
    db_path = tmp_path / "test_vec_fail.db"

    # Mock sqlite_vec.load and logger
    with patch("mnemo_mcp.db.sqlite_vec.load", side_effect=RuntimeError("Extension load failed")),          patch("mnemo_mcp.db.logger") as mock_logger:

        db = MemoryDB(db_path, embedding_dims=768)

        # Should have logged a warning
        assert mock_logger.warning.called
        args, _ = mock_logger.warning.call_args
        assert "sqlite-vec load failed: Extension load failed" in args[0]

        # Vector search should be disabled
        assert db.vec_enabled is False
        assert db._vec_enabled is False

        db.close()
