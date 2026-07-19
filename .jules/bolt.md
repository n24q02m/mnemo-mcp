## 2026-07-07 - Optimize JSON payload serialization
**Learning:** Returning large JSON lists of objects (like search or list results) with `indent=2` adds significant byte overhead due to unnecessary whitespace and newlines, hurting serialization performance and increasing network latency/token cost.
**Action:** Replaced `json.dumps(obj, indent=2)` with `json.dumps(obj, separators=(",", ":"))` in `_json` helper to eliminate all unnecessary whitespace from MCP tool responses while preserving schema compatibility.

## 2026-07-07 - Use json_each for multi-column IN clauses in SQLite
**Learning:** For multi-column IN clauses (like (name, entity_type)), dynamically generating batch queries with `f"IN (VALUES {placeholders})"` and unrolling parameters adds Python-side string interpolation and looping overhead while hitting `SQLITE_MAX_VARIABLE_NUMBER` limits.
**Action:** Replace batched multi-column IN clauses with a single parameter containing a JSON array of tuples and query it using `IN (SELECT json_extract(value, '$[0]'), json_extract(value, '$[1]') FROM json_each(?))`. This is both faster and eliminates the need for loop-based parameter batching.

## $(date +%Y-%m-%d) - Atomic Upsert Optimization
**Learning:** The `upsert_sync_state` logic in `src/mnemo_mcp/db.py` previously used a "Read-Modify-Write" pattern: it queried the database to fetch existing state, merged it in Python using `dict` and conditional logic, and then executed an `INSERT OR REPLACE`. This incurred unnecessary N+1 overhead and Python object instantiation, while being susceptible to Time-of-Check to Time-of-Use (TOCTOU) race conditions.
**Action:** Replace "Read-Modify-Write" patterns for conditional inserts with atomic SQLite `INSERT ... ON CONFLICT DO UPDATE SET` operations. By leveraging `COALESCE(excluded.field, field)`, you can instruct the database engine to preserve existing values if new ones are omitted, completely eliminating the preliminary `SELECT` and Python-side merging overhead.
