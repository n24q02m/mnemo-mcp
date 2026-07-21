## 2026-07-07 - Optimize JSON payload serialization
**Learning:** Returning large JSON lists of objects (like search or list results) with `indent=2` adds significant byte overhead due to unnecessary whitespace and newlines, hurting serialization performance and increasing network latency/token cost.
**Action:** Replaced `json.dumps(obj, indent=2)` with `json.dumps(obj, separators=(",", ":"))` in `_json` helper to eliminate all unnecessary whitespace from MCP tool responses while preserving schema compatibility.

## 2026-07-07 - Use json_each for multi-column IN clauses in SQLite
**Learning:** For multi-column IN clauses (like (name, entity_type)), dynamically generating batch queries with `f"IN (VALUES {placeholders})"` and unrolling parameters adds Python-side string interpolation and looping overhead while hitting `SQLITE_MAX_VARIABLE_NUMBER` limits.
**Action:** Replace batched multi-column IN clauses with a single parameter containing a JSON array of tuples and query it using `IN (SELECT json_extract(value, '$[0]'), json_extract(value, '$[1]') FROM json_each(?))`. This is both faster and eliminates the need for loop-based parameter batching.

## 2026-07-21 - Optimize partial upserts with ON CONFLICT
**Learning:** When implementing 'upsert' logic in SQLite (insert or replace while preserving partial existing data), the 'Read-Modify-Write' pattern (a preliminary `SELECT` followed by Python merging and `INSERT OR REPLACE`) adds N+1 query overhead and TOCTOU issues.
**Action:** Replace 'Read-Modify-Write' upserts with a single atomic query using `INSERT INTO ... ON CONFLICT(...) DO UPDATE SET field = COALESCE(excluded.field, field)`. This bypasses N+1 query overhead, Python object instantiation, and eliminates TOCTOU race conditions.
