
import sqlite3
import time
import json
import uuid
import sys
from pathlib import Path

# Add src to path to import MemoryDB
sys.path.insert(0, str(Path("src").resolve()))
from mnemo_mcp.db import MemoryDB

# Setup DB path
db_path = Path("benchmark.db")
if db_path.exists():
    db_path.unlink()

db = MemoryDB(db_path, embedding_dims=0)

# Pre-fill some data to simulate existing records
existing_ids = set()
for i in range(5000):
    mid = uuid.uuid4().hex[:12]
    existing_ids.add(mid)
    db.add(f"existing content {i}", embedding=None)
    # Manually update ID to match if add generates a new one (it returns ID, so we are good)
    # Actually add returns generated ID. So we should use that.
    # But wait, add generates random ID. We want controlled IDs for testing merge.
    # Let's just insert directly for setup.

db.close()
db_path.unlink()
db = MemoryDB(db_path, embedding_dims=0)

# Generate 10k items, half of which are existing
# We need to know existing IDs.
# Let's insert 5000 items first using `add` and record their IDs.
existing_ids = []
for i in range(5000):
    mid = db.add(f"existing {i}")
    existing_ids.append(mid)

data = []
for i in range(10000):
    if i < 5000:
        mid = existing_ids[i]
    else:
        mid = uuid.uuid4().hex[:12]

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

# Run Import
print("Running MemoryDB.import_jsonl...")
start = time.perf_counter()
stats = db.import_jsonl(jsonl_str, mode="merge")
end = time.perf_counter()
print(f"Time: {(end - start) * 1000:.2f}ms")
print(f"Stats: {stats}")

# Cleanup
db.close()
if db_path.exists():
    db_path.unlink()
