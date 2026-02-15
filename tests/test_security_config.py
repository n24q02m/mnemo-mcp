import pytest
import json
from unittest.mock import MagicMock
from mnemo_mcp.db import MemoryDB
from mnemo_mcp.server import config

@pytest.fixture
def ctx_with_db(tmp_path):
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
async def test_config_set_sync_remote_injection(ctx_with_db):
    ctx, _ = ctx_with_db
    # Try to set a remote that starts with a dash, which could be an argument injection
    result = json.loads(
        await config(
            action="set",
            key="sync_remote",
            value="--config=/etc/passwd",
            ctx=ctx,
        )
    )
    # This should now fail
    assert "error" in result
    assert "alphanumeric" in result["error"]

@pytest.mark.asyncio
async def test_config_set_sync_folder_traversal(ctx_with_db):
    ctx, _ = ctx_with_db
    # Try to set a folder that traverses directories
    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value="../../etc",
            ctx=ctx,
        )
    )
    # This should now fail
    assert "error" in result
    assert "contain '..'" in result["error"]

@pytest.mark.asyncio
async def test_config_set_sync_folder_absolute(ctx_with_db):
    ctx, _ = ctx_with_db
    # Try to set an absolute path
    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value="/etc/passwd",
            ctx=ctx,
        )
    )
    # This should now fail
    assert "error" in result
    assert "relative path" in result["error"]

@pytest.mark.asyncio
async def test_config_set_sync_folder_flags(ctx_with_db):
    ctx, _ = ctx_with_db
    # Try to set a folder starting with -
    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value="-flags",
            ctx=ctx,
        )
    )
    # This should now fail
    assert "error" in result
    assert "start with '-'" in result["error"]

@pytest.mark.asyncio
async def test_config_set_valid(ctx_with_db):
    ctx, _ = ctx_with_db
    # Valid remote
    result = json.loads(
        await config(
            action="set",
            key="sync_remote",
            value="my-drive_2",
            ctx=ctx,
        )
    )
    assert result["status"] == "updated"

    # Valid folder
    result = json.loads(
        await config(
            action="set",
            key="sync_folder",
            value="mnemo/backups",
            ctx=ctx,
        )
    )
    assert result["status"] == "updated"
