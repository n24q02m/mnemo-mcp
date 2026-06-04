## 2025-06-04 - [Fix JSON array filtering to prevent SQL injection and DoS]
**Vulnerability:** SQL injection vulnerability and DoS (Denial of Service) risk in filtering logic for JSON arrays (tags) in `src/mnemo_mcp/db.py`.
**Learning:** Using `q = ",".join(["?"] * len(tags))` and injecting it into the SQL string causes an unbounded number of parameters, potentially hitting SQLite's maximum variable limit (default 999) which crashes the application.
**Prevention:** Use `json_each(?)` with a single JSON string parameter (e.g. `WHERE value IN (SELECT value FROM json_each(?))`) and `json.dumps(tags)` for `tags` filter, avoiding unrolling dynamic placeholders.
