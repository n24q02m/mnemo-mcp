## 2026-02-13 - N+1 in Vector Search
**Learning:** SQLite's speed can mask N+1 query patterns in benchmarks with small datasets, but replacing them with batch fetching (`WHERE id IN (...)`) is still a best practice for scalability and reducing syscall overhead.
**Action:** Always check loop bodies for database queries and lift them out using batch operations.
