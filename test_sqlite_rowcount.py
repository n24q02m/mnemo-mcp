import sqlite3

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
cursor.execute("CREATE TABLE test (id TEXT PRIMARY KEY)")

# Individual inserts
cursor.execute("INSERT OR IGNORE INTO test VALUES (?)", ("1",))
print(f"Single 1 rowcount: {cursor.rowcount}") # Should be 1
cursor.execute("INSERT OR IGNORE INTO test VALUES (?)", ("1",))
print(f"Single 1 (ignore) rowcount: {cursor.rowcount}") # Should be 0

# executemany
data = [("2",), ("3",), ("2",)]
cursor.executemany("INSERT OR IGNORE INTO test VALUES (?)", data)
print(f"executemany [2, 3, 2] rowcount: {cursor.rowcount}") # Expecting 2

# Cleanup and more complex
cursor.execute("DELETE FROM test")
data = [("1",), ("1",), ("2",)]
cursor.executemany("INSERT OR IGNORE INTO test VALUES (?)", data)
print(f"executemany [1, 1, 2] rowcount: {cursor.rowcount}") # Expecting 2
