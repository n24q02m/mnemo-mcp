## 2024-05-22 - Batch Import Optimization
**Learning:** `executemany` with `INSERT OR IGNORE` in SQLite is significantly faster than loop-based `SELECT` then `INSERT` (N+1), reducing overhead by ~20-30% even for small batches. Also, avoid eager evaluation of default arguments in `dict.get(key, func())` which can cause unnecessary computation.
**Action:** Always prefer batch SQL operations for bulk data processing and check for eager evaluation pitfalls in Python.
