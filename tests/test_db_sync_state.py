
from mnemo_mcp.db import MemoryDB


class TestSyncState:
    def test_get_sync_state_nonexistent(self, tmp_db: MemoryDB):
        assert tmp_db.get_sync_state("nonexistent") is None

    def test_upsert_sync_state_initial(self, tmp_db: MemoryDB):
        tmp_db.upsert_sync_state(
            backend="s3",
            last_sync_at=123.456,
            last_commit_sha="abc123",
            upload_cursor=10,
        )
        state = tmp_db.get_sync_state("s3")
        assert state is not None
        assert state["backend"] == "s3"
        assert state["last_sync_at"] == 123.456
        assert state["last_commit_sha"] == "abc123"
        assert state["upload_cursor"] == 10

    def test_upsert_sync_state_partial_update(self, tmp_db: MemoryDB):
        # Initial insert
        tmp_db.upsert_sync_state(
            backend="gdrive", last_sync_at=100.0, last_commit_sha="init", upload_cursor=1
        )

        # Partial update - only update cursor
        tmp_db.upsert_sync_state(backend="gdrive", upload_cursor=2)

        state = tmp_db.get_sync_state("gdrive")
        assert state is not None
        assert state["upload_cursor"] == 2
        assert state["last_sync_at"] == 100.0
        assert state["last_commit_sha"] == "init"

    def test_upsert_sync_state_null_to_value(self, tmp_db: MemoryDB):
        # Initial insert with NULLs
        tmp_db.upsert_sync_state(backend="null_test")
        state = tmp_db.get_sync_state("null_test")
        assert state is not None
        assert state["last_sync_at"] is None
        assert state["last_commit_sha"] is None
        assert state["upload_cursor"] is None

        # Update NULLs to values
        tmp_db.upsert_sync_state(
            backend="null_test", last_sync_at=200.0, upload_cursor=5
        )
        state = tmp_db.get_sync_state("null_test")
        assert state is not None
        assert state["last_sync_at"] == 200.0
        assert state["upload_cursor"] == 5
        assert state["last_commit_sha"] is None

    def test_get_sync_state_table_missing(self, tmp_db: MemoryDB):
        # Drop the table to trigger sqlite3.OperationalError in get_sync_state
        tmp_db._conn.execute("DROP TABLE sync_state")
        tmp_db._conn.commit()

        assert tmp_db.get_sync_state("s3") is None

    def test_get_sync_state_no_row_factory(self, tmp_db: MemoryDB):
        # Force a case where row is not a sqlite3.Row by temporarily changing row_factory
        old_factory = tmp_db._conn.row_factory
        try:
            tmp_db._conn.row_factory = None
            tmp_db.upsert_sync_state(backend="raw_test", upload_cursor=42)
            state = tmp_db.get_sync_state("raw_test")
            assert state is not None
            assert state["backend"] == "raw_test"
            assert state["upload_cursor"] == 42
        finally:
            tmp_db._conn.row_factory = old_factory
