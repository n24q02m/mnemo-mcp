import sys

with open('src/mnemo_mcp/db.py', 'r') as f:
    content = f.read()

# Fix the missing newline before archive_old_memories if it exists
content = content.replace('        return imported, skipped, rejected\n    def archive_old_memories(', '        return imported, skipped, rejected\n\n    def archive_old_memories(')

with open('src/mnemo_mcp/db.py', 'w') as f:
    f.write(content)
