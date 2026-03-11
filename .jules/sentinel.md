## 2025-03-09 - Protect against malformed JSON in `json_each` DoS
**Vulnerability:** Unvalidated JSON strings inserted into SQLite columns queried with `json_each()` will cause a query-crashing exception (`malformed JSON`), creating a potential Denial-of-Service vulnerability.
**Learning:** `json_each` raises exceptions when passed malformed JSON. This is an issue when filtering is done directly via SQL queries.
**Prevention:** Guard `json_each()` calls with `json_valid()` (e.g., `json_valid(column) AND EXISTS(SELECT 1 FROM json_each(column)...)`).
## 2024-05-18 - 🛡️ Sentinel: [HIGH] Fix Unbounded Search Limit DoS
**Vulnerability:** The internal `_handle_search` and `_handle_list` functions in `src/mnemo_mcp/server.py` passed the user-controlled `limit` parameter directly to the database layer without clamping it, causing a potential Denial-of-Service (DoS) via resource exhaustion if called with extremely large values.
**Learning:** To prevent Denial of Service (DoS) attacks via resource exhaustion, pagination or result limits in endpoints must be strictly clamped to a reasonable maximum (e.g., `limit = max(1, min(limit, 100))`) before being passed to the database layer.
**Prevention:** Always clamp limits at the earliest possible entry point to internal functions, even if a higher-level tool wrapper implements its own clamping, to provide defense-in-depth and protect against internal misuses.
