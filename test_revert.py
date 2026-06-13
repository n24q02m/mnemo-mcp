file_path = "src/mnemo_mcp/db.py"
with open(file_path) as f:
    content = f.read()

search_text = """            payloads = []
            for row in rows:
                row_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
                content_val = row["content"] if isinstance(row, sqlite3.Row) else row[1]
                created_at = (
                    row["created_at"] if isinstance(row, sqlite3.Row) else row[2]
                )
                digest = hashlib.sha256((content_val or "").encode("utf-8")).hexdigest()
                payloads.append((digest, created_at, row_id))

            if payloads:
                self._conn.executemany(
                    "UPDATE memories SET "
                    "  commit_sha = COALESCE(commit_sha, ?), "
                    "  valid_from = COALESCE(valid_from, ?) "
                    "WHERE id = ?",
                    payloads,
                )"""

replace_text = """            for row in rows:
                row_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
                content = row["content"] if isinstance(row, sqlite3.Row) else row[1]
                created_at = (
                    row["created_at"] if isinstance(row, sqlite3.Row) else row[2]
                )
                digest = hashlib.sha256((content or "").encode("utf-8")).hexdigest()
                self._conn.execute(
                    "UPDATE memories SET "
                    "  commit_sha = COALESCE(commit_sha, ?), "
                    "  valid_from = COALESCE(valid_from, ?) "
                    "WHERE id = ?",
                    (digest, created_at, row_id),
                )"""

if search_text in content:
    new_content = content.replace(search_text, replace_text)
    with open(file_path, "w") as f:
        f.write(new_content)
    print("Successfully reverted src/mnemo_mcp/db.py")
else:
    print("Search text not found")
