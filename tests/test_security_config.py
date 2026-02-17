
import json
from unittest.mock import MagicMock

import pytest

from mnemo_mcp.db import MemoryDB
from mnemo_mcp.server import config


@pytest.fixture
def ctx_with_db(tmp_path):
    """Mock MCP Context with fresh DB."""
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
async def test_set_insecure_sync_folder(ctx_with_db):
    ctx, _ = ctx_with_db
    # Try to set a path traversal payload
    payload = "../../../etc/passwd"
    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value=payload,
            ctx=ctx,
        )
    )
    # Assert validation failure
    assert "error" in result
    assert "Invalid sync_folder" in result["error"]

@pytest.mark.asyncio
async def test_set_insecure_sync_remote(ctx_with_db):
    ctx, _ = ctx_with_db
    # Try to set a flag-like payload
    payload = "-P"
    result = json.loads(
        await config(
            action="set",
            key="sync_remote",
            value=payload,
            ctx=ctx,
        )
    )
    # Assert validation failure
    assert "error" in result
    assert "Invalid sync_remote" in result["error"]
