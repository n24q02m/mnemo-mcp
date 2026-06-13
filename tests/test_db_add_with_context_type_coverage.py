import json

import pytest

from mnemo_mcp.db import MAX_CONTENT_LENGTH, MemoryDB


class TestAddWithContextTypeCoverage:
    def test_add_with_all_params(self, tmp_db: MemoryDB):
        """Verifies that all parameters are correctly stored in the database."""
        mid = tmp_db.add_with_context_type(
            content="test content",
            context_type="fact",
            category="custom-cat",
            tags=["tag1", "tag2"],
            source="test-source",
            importance=0.8,
            text_raw="raw content",
            compressed=True,
            compression_provider="openai",
        )

        mem = tmp_db.get(mid)
        assert mem is not None
        assert mem["content"] == "test content"
        assert mem["context_type"] == "fact"
        assert mem["category"] == "custom-cat"
        assert json.loads(mem["tags"]) == ["tag1", "tag2"]
        assert mem["source"] == "test-source"
        assert mem["importance"] == 0.8
        assert mem["text_raw"] == "raw content"
        assert mem["compressed"] == 1
        assert mem["compression_provider"] == "openai"

    def test_importance_clamping(self, tmp_db: MemoryDB):
        """Verifies that importance is clamped to [0.0, 1.0]."""
        mid_high = tmp_db.add_with_context_type("high", importance=1.5)
        mid_low = tmp_db.add_with_context_type("low", importance=-0.5)

        assert tmp_db.get(mid_high)["importance"] == 1.0
        assert tmp_db.get(mid_low)["importance"] == 0.0

    def test_content_too_long(self, tmp_db: MemoryDB):
        """Verifies that ValueError is raised when content exceeds MAX_CONTENT_LENGTH."""
        with pytest.raises(ValueError, match="exceeds limit"):
            tmp_db.add_with_context_type("a" * (MAX_CONTENT_LENGTH + 1))

    def test_no_importance(self, tmp_db: MemoryDB):
        """Verifies that the branch without importance works (importance is None)."""
        mid = tmp_db.add_with_context_type("no importance", importance=None)
        mem = tmp_db.get(mid)
        assert mem is not None
        # Default in DB schema is 0.5
        assert mem["importance"] == 0.5

    def test_with_embedding(self, tmp_path):
        """Verifies that embedding is stored in the memories_vec table if vec_enabled."""
        db_path = tmp_path / "vec.db"
        # Need vec enabled to test this branch
        db = MemoryDB(db_path, embedding_dims=4)
        try:
            mid = db.add_with_context_type("vec test", embedding=[0.1, 0.2, 0.3, 0.4])

            # Check memories_vec table using the internal connection which has sqlite-vec loaded
            row = db._conn.execute(
                "SELECT id FROM memories_vec WHERE id = ?", (mid,)
            ).fetchone()
            assert row is not None
            assert row[0] == mid
        finally:
            db.close()

    def test_tags_none_and_empty(self, tmp_db: MemoryDB):
        """Verifies Bolt Performance Optimization for tags_json."""
        mid1 = tmp_db.add_with_context_type("tags none", tags=None)
        mid2 = tmp_db.add_with_context_type("tags empty", tags=[])

        assert tmp_db.get(mid1)["tags"] == "[]"
        assert tmp_db.get(mid2)["tags"] == "[]"

    def test_tags_list(self, tmp_db: MemoryDB):
        """Verifies tags list is correctly serialized."""
        mid = tmp_db.add_with_context_type("tags list", tags=["a"])
        assert tmp_db.get(mid)["tags"] == '["a"]'
