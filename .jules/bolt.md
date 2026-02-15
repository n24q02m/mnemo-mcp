## 2026-02-15 - Vector Search N+1 Optimization
**Learning:** `sqlite-vec` usage often requires careful handling of result hydration. Fetching full records individually for each vector search result creates a significant N+1 bottleneck.
**Action:** Always batch fetch missing records using `WHERE id IN (...)` after retrieving vector scores, and respect SQLite's parameter limits (chunks of ~500) when constructing `IN` clauses.
