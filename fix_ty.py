import re

with open("tests/test_db.py", "r") as f:
    content = f.read()

# Fix for line 587
content = content.replace('mem = tmp_db.get(mid)\n        assert mem["importance"] == 1.0', 'mem = tmp_db.get(mid)\n        assert mem is not None\n        assert mem["importance"] == 1.0')

# Fix for line 591
content = content.replace('mem = tmp_db.get(mid)\n        assert mem["importance"] == 0.0', 'mem = tmp_db.get(mid)\n        assert mem is not None\n        assert mem["importance"] == 0.0')

with open("tests/test_db.py", "w") as f:
    f.write(content)

print("Modification complete.")
