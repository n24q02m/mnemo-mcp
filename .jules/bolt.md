## 2024-05-24 - [SQLite Bulk Import]
**Learning:** `executemany` with `INSERT OR IGNORE` in `sqlite3` correctly returns the count of *inserted* rows in `rowcount`. This allows efficient calculation of skipped duplicates (`total - rowcount`) without N+1 `SELECT` checks.
**Action:** Use this pattern for all bulk data ingestion in SQLite.
