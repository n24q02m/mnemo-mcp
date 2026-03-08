## 2024-03-08 - [Add defensive json_valid check to avoid DoS]
**Vulnerability:** Unvalidated JSON strings in the SQLite database could cause a query-crashing exception (`malformed JSON`) when `json_each` is used.
**Learning:** `json_each` in SQLite raises an error if the input is not valid JSON. This can be exploited by an attacker to cause a Denial of Service by inserting invalid JSON into a column that is later queried with `json_each`.
**Prevention:** Guard `json_each` calls with `json_valid` checks (e.g., `json_valid(column) AND EXISTS(SELECT 1 FROM json_each(column)...)`) to safely filter out invalid JSON without crashing the query.
