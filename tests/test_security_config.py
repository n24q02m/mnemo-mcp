
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mnemo_mcp.db import MemoryDB
from mnemo_mcp.server import config


@pytest.fixture
def ctx_with_db(tmp_path: Path):
    db = MemoryDB(tmp_path / "server_test.db", embedding_dims=0)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "db": db,
        "embedding_model": None,
        "embedding_dims": 0,
    }
    yield ctx, db
    db.close()

@pytest.mark.asyncio
async def test_set_sync_folder_traversal(ctx_with_db):
    ctx, _ = ctx_with_db

    # Try to set a path traversal payload
    payload = "../../../../etc/passwd"

    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value=payload,
            ctx=ctx,
        )
    )

    # Assert that it WAS blocked (security fix verification)
    assert "error" in result
    assert "sync_folder cannot contain '..'" in result["error"]

    # Verify absolute path blocking
    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value="/tmp/test",
            ctx=ctx,
        )
    )
    assert "error" in result
    assert "sync_folder must be a relative path" in result["error"]

    print("\nSecurity verification: path traversal and absolute paths are blocked.")

@pytest.mark.asyncio
async def test_set_sync_remote_validation(ctx_with_db):
    ctx, _ = ctx_with_db

    # Try to set a remote starting with -
    result = json.loads(
        await config(
            action="set",
            key="sync_remote",
            value="-v",
            ctx=ctx,
        )
    )
    assert "error" in result
    assert "sync_remote cannot start with '-'" in result["error"]

    # Try to set a remote with invalid chars
    result = json.loads(
        await config(
            action="set",
            key="sync_remote",
            value="my;remote",
            ctx=ctx,
        )
    )
    assert "error" in result
    assert "sync_remote contains invalid characters" in result["error"]

    # Valid remote should pass
    result = json.loads(
        await config(
            action="set",
            key="sync_remote",
            value="gdrive-backup",
            ctx=ctx,
        )
    )
    assert result["status"] == "updated"
