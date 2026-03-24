## 2026-03-24 - Batch delete in archive_old_memories
**Learning:** O(N) tuple instantiation and executing `INSERT` and `DELETE` pairs within a loop leads to performance bottlenecks when managing a large number of memories in SQLite. SQLite runs significantly faster with pure SQL compound queries.
**Action:** Used `INSERT INTO archived_memories SELECT ... FROM memories` to copy bulk data, followed by a separate bulk `DELETE FROM memories`. This change avoids iterative looping and N+1 query execution, accelerating execution times natively in SQLite engine.
