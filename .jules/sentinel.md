## 2025-03-09 - Protect against malformed JSON in `json_each` DoS
**Vulnerability:** Unvalidated JSON strings inserted into SQLite columns queried with `json_each()` will cause a query-crashing exception (`malformed JSON`), creating a potential Denial-of-Service vulnerability.
**Learning:** `json_each` raises exceptions when passed malformed JSON. This is an issue when filtering is done directly via SQL queries.
**Prevention:** Guard `json_each()` calls with `json_valid()` (e.g., `json_valid(column) AND EXISTS(SELECT 1 FROM json_each(column)...)`).
## 2024-05-24 - Unbounded Search Limit causing potential DoS
**Vulnerability:** Unbounded `limit` parameter in the `_handle_search` and `_handle_list` functions allowed for potential Denial of Service (DoS) attacks by requesting an excessively large number of records.
**Learning:** Always validate and clamp integer limits received from user inputs or tool requests before passing them to the database layer, to prevent memory exhaustion and excessive database load.
**Prevention:** Ensured limits are clamped using `max(1, min(limit, 100))` directly before the `db.search` and `db.list_memories` calls in the server handlers.
