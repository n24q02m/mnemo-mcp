
import sqlite3
import time
import json
import uuid

# Setup DB
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, category TEXT, tags TEXT, source TEXT, created_at TEXT, updated_at TEXT, access_count INTEGER, last_accessed TEXT)")

# Generate large JSONL
data = []
for i in range(10000):
    item = {
        "id": uuid.uuid4().hex,
        "content": f"content {i}",
        "category": "general",
        "tags": ["tag1", "tag2"],
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
        "access_count": 0,
        "last_accessed": "2023-01-01T00:00:00"
    }
    data.append(json.dumps(item))
jsonl_str = "\n".join(data)

# Baseline: One by one
def import_one_by_one(conn, jsonl_str):
    start = time.perf_counter()
    for line in jsonl_str.split("\n"):
        mem = json.loads(line)
        conn.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (mem["id"], mem["content"], mem["category"], json.dumps(mem["tags"]), None, mem["created_at"], mem["updated_at"], mem["access_count"], mem["last_accessed"])
        )
    conn.commit()
    print(f"One by one: {(time.perf_counter() - start) * 1000:.2f}ms")

# Optimization: executemany
def import_executemany(conn, jsonl_str):
    start = time.perf_counter()
    rows = []
    for line in jsonl_str.split("\n"):
        mem = json.loads(line)
        rows.append((mem["id"], mem["content"], mem["category"], json.dumps(mem["tags"]), None, mem["created_at"], mem["updated_at"], mem["access_count"], mem["last_accessed"]))

    conn.executemany(
        "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    print(f"Executemany: {(time.perf_counter() - start) * 1000:.2f}ms")

# Run Baseline
conn.execute("DELETE FROM memories")
import_one_by_one(conn, jsonl_str)

# Run Optimization
conn.execute("DELETE FROM memories")
import_executemany(conn, jsonl_str)
