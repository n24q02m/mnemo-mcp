import sqlite3
import uuid
from datetime import datetime, UTC

def test_row_values():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE test (name TEXT, type TEXT, id TEXT)")
    conn.execute("INSERT INTO test VALUES ('A', 'concept', 'id1')")
    conn.execute("INSERT INTO test VALUES ('B', 'tool', 'id2')")

    # Try the syntax used in graph.py
    placeholders = "(?, ?), (?, ?)"
    params = ["A", "concept", "B", "tool"]
    query = f"SELECT name, type, id FROM test WHERE (name, type) IN (VALUES {placeholders})"
    print(f"Query: {query}")
    try:
        rows = conn.execute(query, params).fetchall()
        print(f"Rows: {rows}")
    except Exception as e:
        print(f"Failed: {e}")

    # Alternative syntax that is more compatible
    query2 = f"SELECT name, type, id FROM test WHERE (name == ? AND type == ?) OR (name == ? AND type == ?)"
    print(f"Alternative Query: {query2}")
    rows2 = conn.execute(query2, params).fetchall()
    print(f"Rows 2: {rows2}")

if __name__ == "__main__":
    test_row_values()
