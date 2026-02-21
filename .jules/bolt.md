## 2024-05-23 - [SQLite JSON Filtering vs Python Filtering]
**Learning:** Post-filtering search results in Python after a database LIMIT clause is incorrect and kills recall. If the top N results from the DB don't match the filter, the user gets 0 results even if matches exist deeper in the dataset.
**Action:** Always push filtering down to the database layer. In SQLite, use `json_each` and `EXISTS` to filter JSON arrays efficiently within the SQL query itself, ensuring the LIMIT applies *after* filtering.
