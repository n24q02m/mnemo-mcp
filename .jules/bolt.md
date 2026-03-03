## 2026-03-03 - SQLite `json_object` Performance Win
**Learning:** Offloading JSON construction directly to the database using `json_object()` and `json()` provides a ~4x speedup over fetching rows into Python dictionaries, running `json.loads` on JSON columns, and then `json.dumps` on the whole row. This avoids a lot of overhead in serialization/deserialization loops within Python.
**Action:** Use native database JSON manipulation functions rather than building data iteratively in application code when bulk exporting serialized structures.
