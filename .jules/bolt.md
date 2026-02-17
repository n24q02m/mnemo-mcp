## 2026-02-17 - sqlite-vec LIMIT constraint
**Learning:** `sqlite-vec` KNN search requires the `ORDER BY distance LIMIT k` clause to be applied directly to the virtual table scan. Using a `JOIN` on the vector table can confuse the query optimizer, leading to "A LIMIT or 'k = ?' constraint is required" error.
**Action:** Use a subquery to encapsulate the vector search (with LIMIT) before joining with other tables.
