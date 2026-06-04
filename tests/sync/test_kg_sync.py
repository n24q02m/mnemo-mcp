import json
from pathlib import Path
import pytest
from mnemo_mcp.db import MemoryDB
from mnemo_mcp.sync.delta import apply_bundle, build_full_bundle

_PASS = "kg-sync-test-passphrase"

@pytest.fixture
def isolated_db(tmp_path: Path):
    db = MemoryDB(tmp_path / "memories.db", embedding_dims=0)
    yield db
    db.close()

async def test_apply_bundle_kg_sections(isolated_db: MemoryDB, tmp_path: Path):
    """
    Verify that apply_bundle correctly applies entities, edges, and links from a bundle,
    and that the optimized executemany logic preserves correctness and count accuracy.
    """
    # Setup source DB with KG sections
    other = MemoryDB(tmp_path / "other.db", embedding_dims=0)

    # 1. Add some memories (needed for foreign key constraints)
    other._conn.execute("INSERT INTO memories (id, content, created_at, updated_at, last_accessed) VALUES ('m1', 'mem1', '2024-01-01', '2024-01-01', '2024-01-01')")
    other._conn.execute("INSERT INTO memories (id, content, created_at, updated_at, last_accessed) VALUES ('m2', 'mem2', '2024-01-01', '2024-01-01', '2024-01-01')")

    # 2. Add entities
    other._conn.execute("INSERT INTO memory_entities (id, name, entity_type, created_at, updated_at) VALUES ('e1', 'Ent1', 'TypeA', '2024-01-01', '2024-01-01')")
    other._conn.execute("INSERT INTO memory_entities (id, name, entity_type, created_at, updated_at) VALUES ('e2', 'Ent2', 'TypeB', '2024-01-01', '2024-01-01')")

    # 3. Add edges
    other._conn.execute("INSERT INTO memory_edges (id, source_id, target_id, relation_type, created_at, memory_id) VALUES ('edge1', 'e1', 'e2', 'relates_to', '2024-01-01', 'm1')")

    # 4. Add links
    other._conn.execute("INSERT INTO memory_entity_links (memory_id, entity_id) VALUES ('m1', 'e1')")
    other._conn.execute("INSERT INTO memory_entity_links (memory_id, entity_id) VALUES ('m2', 'e2')")

    other._conn.commit()

    # Build bundle
    bundle = await build_full_bundle(other, passphrase=_PASS)
    other.close()

    # Apply to isolated_db
    counts = await apply_bundle(isolated_db, bundle, _PASS)

    assert counts["entities_applied"] == 2
    assert counts["edges_applied"] == 1
    assert counts["links_applied"] == 2

    # Verify DB state
    ents = isolated_db._conn.execute("SELECT name FROM memory_entities ORDER BY name").fetchall()
    assert [e["name"] for e in ents] == ["Ent1", "Ent2"]

    edges = isolated_db._conn.execute("SELECT id FROM memory_edges").fetchall()
    assert len(edges) == 1
    assert edges[0]["id"] == "edge1"

    links = isolated_db._conn.execute("SELECT memory_id, entity_id FROM memory_entity_links ORDER BY memory_id").fetchall()
    assert len(links) == 2
    assert links[0]["memory_id"] == "m1"
    assert links[1]["memory_id"] == "m2"

async def test_apply_bundle_kg_idempotency(isolated_db: MemoryDB, tmp_path: Path):
    """
    Verify that re-applying the same KG sections results in 0 applied counts
    due to INSERT OR IGNORE behavior.
    """
    other = MemoryDB(tmp_path / "other.db", embedding_dims=0)
    other._conn.execute("INSERT INTO memory_entities (id, name, entity_type, created_at, updated_at) VALUES ('e1', 'Ent1', 'TypeA', '2024-01-01', '2024-01-01')")
    other._conn.commit()
    bundle = await build_full_bundle(other, passphrase=_PASS)
    other.close()

    # Apply once
    counts1 = await apply_bundle(isolated_db, bundle, _PASS)
    assert counts1["entities_applied"] == 1

    # Apply again (should be ignored by INSERT OR IGNORE)
    counts2 = await apply_bundle(isolated_db, bundle, _PASS)
    assert counts2["entities_applied"] == 0
