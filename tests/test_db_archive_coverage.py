from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from mnemo_mcp.db import MemoryDB


class TestArchiveByScoreCoverage:
    def test_archive_by_score_basic(self, tmp_db: MemoryDB):
        # 1. Row that should be archived
        # archive_after_days = 10, days_since = 20 -> recency_factor = 2.0
        # importance = 0.4 -> (1 - 0.4) = 0.6
        # score = 2.0 * 0.6 = 1.2
        # 1.2 > 1.0 (default threshold) -> archive
        mid1 = tmp_db.add("should archive")
        tmp_db.update_importance(mid1, 0.4)
        old_date = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid1)
        )

        # 2. Row that should NOT be archived (recent)
        # recency_factor = 5/10 = 0.5
        # score = 0.5 * 0.6 = 0.3 <= 1.0
        mid2 = tmp_db.add("recent")
        tmp_db.update_importance(mid2, 0.4)
        recent_date = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (recent_date, mid2)
        )

        # 3. Row that should NOT be archived (important)
        # recency_factor = 2.0
        # importance = 0.9 -> (1 - 0.9) = 0.1
        # score = 2.0 * 0.1 = 0.2 <= 1.0
        mid3 = tmp_db.add("important")
        tmp_db.update_importance(mid3, 0.9)
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid3)
        )

        tmp_db._conn.commit()

        count = tmp_db.archive_by_score(archive_after_days=10)
        assert count == 1

        mem1 = tmp_db.get(mid1)
        assert mem1["archived_at"] is not None

        mem2 = tmp_db.get(mid2)
        assert mem2["archived_at"] is None

        mem3 = tmp_db.get(mid3)
        assert mem3["archived_at"] is None

    def test_archive_by_score_threshold(self, tmp_db: MemoryDB):
        # recency_factor = 2.0, importance = 0.5 -> score = 2.0 * 0.5 = 1.0
        # score > threshold. If threshold=0.9, it archives.
        mid = tmp_db.add("threshold test")
        tmp_db.update_importance(mid, 0.5)
        old_date = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid)
        )
        tmp_db._conn.commit()

        count = tmp_db.archive_by_score(archive_after_days=10, score_threshold=1.1)
        assert count == 0

        count = tmp_db.archive_by_score(archive_after_days=10, score_threshold=0.9)
        assert count == 1
        assert tmp_db.get(mid)["archived_at"] is not None

    def test_archive_by_score_empty(self, tmp_db: MemoryDB):
        assert tmp_db.archive_by_score() == 0

    def test_archive_by_score_no_active_memories(self, tmp_db: MemoryDB):
        mid = tmp_db.add("already archived")
        tmp_db._conn.execute(
            "UPDATE memories SET archived_at = '2023-01-01' WHERE id = ?", (mid,)
        )
        tmp_db._conn.commit()
        assert tmp_db.archive_by_score() == 0

    def test_archive_by_score_invalid_date(self, tmp_db: MemoryDB):
        mid = tmp_db.add("invalid date")
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = 'garbage' WHERE id = ?", (mid,)
        )
        tmp_db._conn.commit()

        # Should just skip it (continue in loop)
        assert tmp_db.archive_by_score() == 0

    def test_archive_by_score_clamped_importance(self, tmp_db: MemoryDB):
        # Test importance > 1.0 (clamped to 1.0)
        mid_high = tmp_db.add("high importance")
        tmp_db.update_importance(mid_high, 1.5)
        # Test importance < 0.0 (clamped to 0.0)
        mid_low = tmp_db.add("low importance")
        tmp_db.update_importance(mid_low, -0.5)

        old_date = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid_high)
        )
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid_low)
        )
        tmp_db._conn.commit()

        # High importance (clamped to 1.0) -> score = recency * (1 - 1.0) = 0.0
        # Low importance (clamped to 0.0) -> score = recency * (1 - 0.0) = recency
        # archive_after_days = 10, days_since = 20 -> recency = 2.0

        count = tmp_db.archive_by_score(archive_after_days=10)
        assert count == 1  # Only mid_low should be archived

        assert tmp_db.get(mid_high)["archived_at"] is None
        assert tmp_db.get(mid_low)["archived_at"] is not None

    def test_archive_by_score_settings_fallback_success(self, tmp_db: MemoryDB):
        mid = tmp_db.add("fallback test")
        tmp_db.update_importance(mid, 0.0)
        old_date = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid)
        )
        tmp_db._conn.commit()

        # Should use settings.archive_after_days (90)
        count = tmp_db.archive_by_score(archive_after_days=None)
        assert count == 1

    def test_archive_by_score_settings_exception(self, tmp_db: MemoryDB):
        mid = tmp_db.add("exception test")
        tmp_db.update_importance(mid, 0.0)
        old_date = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid)
        )
        tmp_db._conn.commit()

        # Trigger Exception by making settings.archive_after_days something non-numeric
        with patch("mnemo_mcp.config.settings") as mock_s:
            mock_s.archive_after_days = "not a number"
            count = tmp_db.archive_by_score(archive_after_days=None)
            assert count == 1  # Still archives because fallback is 90

    def test_archive_after_days_minimum_one(self, tmp_db: MemoryDB):
        mid = tmp_db.add("min test")
        tmp_db.update_importance(mid, 0.0)
        old_date = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        tmp_db._conn.execute(
            "UPDATE memories SET updated_at = ? WHERE id = ?", (old_date, mid)
        )
        tmp_db._conn.commit()

        # archive_after_days = max(1, int(0)) = 1
        count = tmp_db.archive_by_score(archive_after_days=0)
        assert count == 1
