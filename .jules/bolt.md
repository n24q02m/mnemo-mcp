## 2025-02-18 - SQLite Bulk Merge Pattern
**Learning:** Python's `sqlite3` `executemany` combined with `INSERT OR IGNORE` correctly reports the number of *inserted* rows via `cursor.rowcount`. This allows tracking "skipped" records (total - rowcount) without needing a prior `SELECT` check for existence, reducing complexity from O(N) queries to O(1) query.
**Action:** Use `INSERT OR IGNORE` with `rowcount` for all bulk merge/deduplication logic instead of explicit existence checks.
