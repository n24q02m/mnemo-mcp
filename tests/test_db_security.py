import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mnemo_mcp.db import MemoryDB


class TestDBSecurity(unittest.TestCase):
    def setUp(self):
        self.mock_conn = MagicMock()
        # Mock fetchone for _ensure_vec_table
        self.mock_conn.execute.return_value.fetchone.return_value = None

        with patch("mnemo_mcp.db.sqlite3"):
            # We need to bypass the initialization that calls executescript
            with patch.object(MemoryDB, "_init_memory_schema"):
                with patch.object(MemoryDB, "_ensure_vec_table"):
                    self.db = MemoryDB(db_path=Path(":memory:"))
                    self.db._conn = self.mock_conn
                    self.db._vec_enabled = True
                    self.db._embedding_dims = 768

    def test_drop_vectors_for_reindex_uses_static_sql(self):
        # Trigger the method
        with patch.object(self.db, "_ensure_vec_table"):
            self.db._drop_vectors_for_reindex()

        # Verify calls to execute
        # We expect two calls to DROP TABLE IF EXISTS
        calls = [call[0][0] for call in self.mock_conn.execute.call_args_list]

        self.assertIn("DROP TABLE IF EXISTS memories_vec", calls)
        self.assertIn("DROP TABLE IF EXISTS memory_entities_vec", calls)

        # Verify no f-string style interpolation was used in a loop (conceptually)
        # by checking that the calls were exactly these static strings.
        for call_str in calls:
            if "DROP TABLE IF EXISTS" in call_str:
                self.assertIn(
                    call_str,
                    [
                        "DROP TABLE IF EXISTS memories_vec",
                        "DROP TABLE IF EXISTS memory_entities_vec",
                    ],
                )

    def test_ensure_vec_table_uses_dims_correctly(self):
        # Reset mock
        self.mock_conn.execute.reset_mock()
        self.mock_conn.execute.return_value.fetchone.return_value = None

        # Use the real method
        MemoryDB._ensure_vec_table(self.db, 512)

        # Verify call
        create_call = self.mock_conn.execute.call_args_list[1][0][0]
        self.assertIn("CREATE VIRTUAL TABLE memories_vec", create_call)
        self.assertIn("embedding float[512]", create_call)


if __name__ == "__main__":
    unittest.main()
