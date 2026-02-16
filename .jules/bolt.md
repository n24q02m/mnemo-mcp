## 2024-05-23 - [N+1 in Hybrid Search]
**Learning:** Hybrid search implementations that combine FTS5 and vector search often require manual merging of results. If the vector search library (like `sqlite-vec`) returns only IDs/distances, fetching the full records one-by-one inside a loop creates a classic N+1 query bottleneck.
**Action:** Always inspect the retrieval logic in hybrid search. Collect all IDs first, then fetch full records in a single batched `IN (...)` query (chunked to respect SQLite limits).
