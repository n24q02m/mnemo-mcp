## 2024-05-24 - SQLite JSON Function Acceleration
**Learning:** For bulk data exports, iterating over Python rows and serializing via `json.dumps()` creates significant overhead. Offloading the JSON construction to SQLite using `json_object()` and `json()` drastically speeds up the process (by ~2x) and completely avoids the Python-side deserialization/reserialization loop.
**Action:** When outputting formatted bulk data from SQLite (like exports), format the strings at the database level instead of in the Python loop.
