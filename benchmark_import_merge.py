
import sqlite3
import time
import json
import uuid

# Setup DB
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, category TEXT, tags TEXT, source TEXT, created_at TEXT, updated_at TEXT, access_count INTEGER, last_accessed TEXT)")

# Pre-fill some data to simulate existing records
existing_ids = set()
for i in range(5000):
    mid = uuid.uuid4().hex
    existing_ids.add(mid)
    conn.execute("INSERT INTO memories (id, content) VALUES (?, ?)", (mid, "existing"))
conn.commit()

# Generate 10k items, half of which are existing
data = []
for i in range(10000):
    if i < 5000:
        mid = list(existing_ids)[i]
    else:
        mid = uuid.uuid4().hex

    item = {
        "id": mid,
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

# Baseline: One by one with individual existence check
def import_one_by_one_merge(conn, jsonl_str):
    start = time.perf_counter()
    skipped = 0
    imported = 0
    for line in jsonl_str.split("\n"):
        mem = json.loads(line)
        # Check existence
        exists = conn.execute("SELECT 1 FROM memories WHERE id = ?", (mem["id"],)).fetchone()
        if exists:
            skipped += 1
            continue

        conn.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (mem["id"], mem["content"], mem["category"], json.dumps(mem["tags"]), None, mem["created_at"], mem["updated_at"], mem["access_count"], mem["last_accessed"])
        )
        imported += 1
    conn.commit()
    print(f"One by one (merge): {(time.perf_counter() - start) * 1000:.2f}ms (skipped={skipped}, imported={imported})")

# Optimization: Batched existence check + executemany
def import_batched_merge(conn, jsonl_str, batch_size=1000):
    start = time.perf_counter()
    skipped = 0
    imported = 0

    lines = jsonl_str.split("\n")
    total = len(lines)

    for i in range(0, total, batch_size):
        batch = lines[i:i+batch_size]
        current_batch_data = []
        batch_ids = []

        # 1. Parse and collect IDs
        for line in batch:
            mem = json.loads(line)
            batch_ids.append(mem["id"])
            current_batch_data.append(mem)

        # 2. Batch check existence
        placeholders = ",".join("?" for _ in batch_ids)
        existing_rows = conn.execute(f"SELECT id FROM memories WHERE id IN ({placeholders})", batch_ids).fetchall()
        existing_set = {row[0] for row in existing_rows}

        # 3. Filter
        to_insert = []
        for mem in current_batch_data:
            if mem["id"] in existing_set:
                skipped += 1
            else:
                to_insert.append((mem["id"], mem["content"], mem["category"], json.dumps(mem["tags"]), None, mem["created_at"], mem["updated_at"], mem["access_count"], mem["last_accessed"]))

        # 4. Batch insert
        if to_insert:
            conn.executemany(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                to_insert
            )
            imported += len(to_insert)

    conn.commit()
    print(f"Batched (merge): {(time.perf_counter() - start) * 1000:.2f}ms (skipped={skipped}, imported={imported})")


# Run Baseline
print("Running Baseline...")
import_one_by_one_merge(conn, jsonl_str)

# Reset and Run Optimization
conn.execute("DELETE FROM memories")
# Re-fill
for mid in existing_ids:
    conn.execute("INSERT INTO memories (id, content) VALUES (?, ?)", (mid, "existing"))
conn.commit()

print("Running Optimization...")
import_batched_merge(conn, jsonl_str)
