
import sqlite3
import time
import uuid

# Setup
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, category TEXT, access_count INTEGER)")
conn.execute("CREATE INDEX idx_memories_category ON memories(category)")

data = [
    (uuid.uuid4().hex, f"content {i}", "tech", 0) for i in range(100000)
]
conn.executemany("INSERT INTO memories VALUES (?, ?, ?, ?)", data)

# 1. COUNT(*)
start = time.perf_counter()
conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
print(f"COUNT(*): {(time.perf_counter() - start) * 1000:.2f}ms")

# 2. GROUP BY category
start = time.perf_counter()
conn.execute("SELECT category, COUNT(*) FROM memories GROUP BY category").fetchall()
print(f"GROUP BY: {(time.perf_counter() - start) * 1000:.2f}ms")

conn.close()
