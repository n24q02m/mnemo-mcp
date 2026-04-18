import json

import pytest

from mnemo_mcp.db import MemoryDB


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    return MemoryDB(db_path)


def test_import_jsonl_modes(db):
    # Initial data
    initial_data = [
        {"id": "1", "content": "Memory 1", "category": "cat1", "importance": 0.1},
        {"id": "2", "content": "Memory 2", "category": "cat2", "importance": 0.2},
    ]
    db.import_jsonl(initial_data, mode="replace")

    assert len(db.list_memories()) == 2
    m1 = db.get("1")
    assert m1["content"] == "Memory 1"
    assert m1["importance"] == 0.1

    # Merge mode (update existing)
    merge_data = [
        {"id": "1", "content": "Memory 1 Updated", "category": "cat1", "importance": 0.9},
        {"id": "3", "content": "Memory 3", "category": "cat3", "importance": 0.3},
    ]
    db.import_jsonl(merge_data, mode="merge")

    assert len(db.list_memories()) == 3
    m1 = db.get("1")
    assert m1["content"] == "Memory 1 Updated"
    assert m1["importance"] == 0.9
    assert db.get("3")["content"] == "Memory 3"

    # Skip mode (ignore existing)
    skip_data = [
        {"id": "2", "content": "Memory 2 Updated", "category": "cat2", "importance": 0.8},
        {"id": "4", "content": "Memory 4", "category": "cat4", "importance": 0.4},
    ]
    db.import_jsonl(skip_data, mode="skip")

    assert len(db.list_memories()) == 4
    m2 = db.get("2")
    assert m2["content"] == "Memory 2"
    assert m2["importance"] == 0.2
    assert db.get("4")["content"] == "Memory 4"

    # Replace mode (clear all)
    replace_data = [
        {"id": "5", "content": "Memory 5", "category": "cat5", "importance": 0.5}
    ]
    db.import_jsonl(replace_data, mode="replace")
    assert len(db.list_memories()) == 1
    assert db.get("5")["content"] == "Memory 5"


def test_import_jsonl_string(db):
    jsonl_data = '{"id": "1", "content": "String Memory"}\n{"id": "2", "content": "Another String Memory"}'
    db.import_jsonl(jsonl_data, mode="replace")
    assert len(db.list_memories()) == 2
    assert db.get("1")["content"] == "String Memory"


def test_import_jsonl_rejected(db):
    # content too long
    long_content = "a" * 6000  # MAX_CONTENT_LENGTH = 5000
    data = [
        {"id": "1", "content": "Short"},
        {"id": "2", "content": long_content},
        {"id": "3", "content": "Valid"},
    ]
    stats = db.import_jsonl(data, mode="replace")
    assert stats["imported"] == 2
    assert stats["rejected"] == 1
    assert len(db.list_memories()) == 2
