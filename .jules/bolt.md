## 2025-03-24 - N+1 Query Optimization in Entity Upserts
**Learning:** For small-to-medium datasets (e.g. graph entity extraction returning 10-200 entities), Python sqlite3 driver's looping `execute` for point reads (using a `SELECT` against a unique index) followed by a bulk `executemany` for inserts and updates is incredibly fast, even faster than constructing massive `IN (VALUES ...)` queries or relying on `executemany` UPSERTs without `RETURNING`.
**Action:** Replaced the N+1 looping `execute(SELECT)` and conditional `execute(INSERT)`/`execute(UPDATE)` statements in `graph.py`'s `upsert_entities` function with an initial loop to deduplicate unique entities and query the DB, followed by unified `conn.executemany` bulk insertions and updates. This delivered measurable ~2x improvements on inserts/updates without relying on external dependencies or risking query size limits.

## 2025-03-24 - JSON Loading Optimization in list_archived
**Learning:** Offloading JSON construction and result set aggregation to SQLite using `json_group_array` and `json_object` is significantly more efficient than manual Python-side iteration and repeated `json.loads` calls.
**Action:** Optimized `list_archived` in `db.py` to use a single aggregated JSON query and a single `json.loads` call. Benchmarked result showed a ~20% performance improvement for typical pagination limits (20-100 rows).
