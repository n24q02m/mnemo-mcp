## 2024-03-24 - [Optimize MemoryDB Export via Native SQLite JSON]
**Learning:** Offloading JSON serialization logic (e.g., dict creation and json formatting) to SQLite's native `json_object` and `json()` functions is significantly faster (~3x in benchmarks) than retrieving rows to Python and converting them sequentially.
**Action:** Use native SQLite queries for dataset serialization operations rather than retrieving pure objects and processing them in Python, avoiding memory bottlenecks for large datasets.
