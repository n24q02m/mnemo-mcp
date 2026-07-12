## 2026-07-07 - Optimize JSON payload serialization
**Learning:** Returning large JSON lists of objects (like search or list results) with `indent=2` adds significant byte overhead due to unnecessary whitespace and newlines, hurting serialization performance and increasing network latency/token cost.
**Action:** Replaced `json.dumps(obj, indent=2)` with `json.dumps(obj, separators=(",", ":"))` in `_json` helper to eliminate all unnecessary whitespace from MCP tool responses while preserving schema compatibility.

## 2026-07-12 - Optimize SQLite conditional UPDATEs by checking cursor.rowcount
**Learning:** Performing a preliminary `SELECT` to check if a row meets conditions before doing an `UPDATE` introduces N+1 overhead and unnecessary Python object instantiation.
**Action:** Execute the conditional `UPDATE` directly and check `cursor.rowcount > 0` to confirm success, pushing the condition evaluation to the SQLite engine and bypassing Python entirely.
