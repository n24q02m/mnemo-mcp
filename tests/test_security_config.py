
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from mnemo_mcp.server import config
from mnemo_mcp.config import settings
from mnemo_mcp.db import MemoryDB

@pytest.fixture
def ctx_with_db(tmp_path: Path):
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
async def test_config_validation(ctx_with_db):
    ctx, _ = ctx_with_db

    # Test valid remote
    result = await config(action="set", key="sync_remote", value="valid_remote", ctx=ctx)
    assert '"status": "updated"' in result
    assert settings.sync_remote == "valid_remote"

    # Test invalid remote (starting with -)
    result = await config(action="set", key="sync_remote", value="-invalid", ctx=ctx)
    assert '"error":' in result
    assert "start with '-'" in result
    # Ensure value was not updated
    assert settings.sync_remote == "valid_remote"

    # Test invalid remote (bad chars)
    result = await config(action="set", key="sync_remote", value="invalid/remote", ctx=ctx)
    assert '"error":' in result
    assert "alphanumeric" in result

    # Test invalid folder (traversal)
    result = await config(action="set", key="sync_folder", value="../parent", ctx=ctx)
    assert '"error":' in result
    assert "cannot contain '..'" in result
    # Ensure value was not updated (default is mnemo-mcp, or previously set value)
    assert settings.sync_folder != "../parent"

    # Test invalid folder (absolute)
    result = await config(action="set", key="sync_folder", value="/etc/passwd", ctx=ctx)
    assert '"error":' in result
    assert "must be relative" in result
