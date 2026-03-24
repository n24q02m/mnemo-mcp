## 2024-05-15 - [Test Bolt Log]
**Learning:** Initial setup.
**Action:** None.

## 2024-05-15 - Bolt Optimization: N+1 Relation Checks
**Learning:** SQLite executemany with INSERT OR IGNORE is significantly faster than querying each relation to avoid duplicates.
**Action:** Replaced N+1 index subqueries with bulk INSERT OR IGNORE in create_relations.
