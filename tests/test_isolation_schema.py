"""DECISION D3: per-sub isolation = sub column on EVERY D1 table + Vectorize
metadata filter by sub. This test is the executable contract; the DDL and
MemoryDBD1 must satisfy it. Rejected alternatives (per-sub index / one-D1-per-sub)
are documented in the plan, not implemented.

Marked xfail(strict) until ``migrations/0001_init_mnemo.sql`` lands (Task 5) and
the sync_state PK fix lands (Task 11); the marker is removed then so the contract
goes live.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.xfail(
    reason="D3 contract; DDL lands in Task 5, sync_state PK in Task 11",
    strict=True,
    raises=(AssertionError, FileNotFoundError),
)

D1_TABLES = {
    "memories",
    "archived_memories",
    "memory_entities",
    "memory_edges",
    "memory_entity_links",
    "sync_state",
    "store_meta",
}


def test_every_d1_table_has_sub_column():
    ddl = Path("migrations/0001_init_mnemo.sql").read_text(encoding="utf-8")
    for table in D1_TABLES:
        m = re.search(
            rf"CREATE TABLE(?: IF NOT EXISTS)?\s+{table}\s*\((.*?)\);",
            ddl,
            re.IGNORECASE | re.DOTALL,
        )
        assert m, f"table {table} missing from DDL"
        body = m.group(1)
        assert re.search(r"\bsub\b\s+TEXT", body, re.IGNORECASE), (
            f"table {table} missing `sub TEXT` column (D3 isolation)"
        )


def test_sync_state_pk_includes_sub():
    ddl = Path("migrations/0001_init_mnemo.sql").read_text(encoding="utf-8")
    m = re.search(
        r"CREATE TABLE(?: IF NOT EXISTS)?\s+sync_state\s*\((.*?)\);",
        ddl,
        re.IGNORECASE | re.DOTALL,
    )
    assert m
    body = re.sub(r"\s+", " ", m.group(1).lower())
    # PK must be (sub, backend) -- not backend alone (mem_002 collision fix).
    assert "primary key (sub, backend)" in body
