## 2024-05-22 - [Optimizing SQLite Bulk Inserts]
**Learning:** `executemany` with `INSERT OR IGNORE` is significantly faster (~40%) than loop-based `SELECT` + `INSERT` for merge operations in SQLite. `rowcount` correctly reports inserted rows for `INSERT OR IGNORE`, allowing accurate stats without extra queries.
**Action:** Use `executemany` for batch processing in SQLite whenever possible, and rely on `rowcount` for stats if using `INSERT OR IGNORE`.
