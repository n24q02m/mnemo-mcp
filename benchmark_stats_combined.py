
import sqlite3
import time
import uuid

# Setup
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, category TEXT, created_at TEXT, updated_at TEXT)")
conn.execute("CREATE INDEX idx_memories_category ON memories(category)")
conn.execute("CREATE INDEX idx_memories_updated ON memories(updated_at)")

data = [
    (uuid.uuid4().hex, f"content {i}", "tech", "2023-01-01", "2023-01-01") for i in range(100000)
]
conn.executemany("INSERT INTO memories VALUES (?, ?, ?, ?, ?)", data)

# 1. Baseline: Separate queries
start = time.perf_counter()
total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
last_updated = conn.execute("SELECT MAX(updated_at) FROM memories").fetchone()[0]
print(f"Separate queries: {(time.perf_counter() - start) * 1000:.2f}ms")

# 2. Optimized: Combined query
start = time.perf_counter()
row = conn.execute("SELECT COUNT(*), MAX(updated_at) FROM memories").fetchone()
total_opt = row[0]
last_updated_opt = row[1]
print(f"Combined query: {(time.perf_counter() - start) * 1000:.2f}ms")

assert total == total_opt
assert last_updated == last_updated_opt

conn.close()
