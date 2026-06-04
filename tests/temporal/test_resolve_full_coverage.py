"""Full coverage tests for mnemo_mcp.temporal.resolve using mocks to ensure cross-platform coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mnemo_mcp.temporal.resolve import (
    _serialize,
    find_similar_entity,
    insert_entity_with_embedding,
)


def test_serialize_padding():
    # Test line 53: padding shorter vectors
    short_vec = [1.0, 2.0]
    serialized = _serialize(short_vec)
    assert len(serialized) == 768 * 4  # 768 floats * 4 bytes

    # Test line 55: truncating longer vectors
    long_vec = [1.0] * 1000
    serialized_long = _serialize(long_vec)
    assert len(serialized_long) == 768 * 4


@patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True)
def test_find_similar_entity_knn_flow(mock_exists):
    mock_conn = MagicMock()
    # Stage 1 miss
    mock_conn.execute.return_value.fetchone.return_value = None

    # Stage 2 KNN hit
    mock_conn.execute.return_value.fetchall.return_value = [(1, 0.1)]  # rowid, distance

    # Stage 2 Entity lookup
    mock_conn.execute.return_value.fetchone.side_effect = [
        None,  # Stage 1 miss
        ("eid-123",),  # Stage 2 hit
    ]

    v = [0.1] * 768
    eid = find_similar_entity(mock_conn, "Similar", "concept", v, threshold=0.5)
    assert eid == "eid-123"


@patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True)
def test_find_similar_entity_low_similarity(mock_exists):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    # distance 2.0 -> similarity 0.0
    mock_conn.execute.return_value.fetchall.return_value = [(1, 2.0)]

    v = [0.1] * 768
    eid = find_similar_entity(mock_conn, "Different", "concept", v, threshold=0.5)
    assert eid is None


@patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True)
def test_insert_entity_with_embedding_missing_rowid(mock_exists):
    mock_conn = MagicMock()
    # actual_id fetch
    mock_conn.execute.return_value.fetchone.side_effect = [
        ("eid-123",),  # actual_id
        None,  # ent_rowid miss
    ]

    eid = insert_entity_with_embedding(mock_conn, "Ghost", "concept", [0.1] * 768)
    assert eid == "eid-123"


@patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True)
def test_insert_entity_with_embedding_exception(mock_exists):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = ("eid-123",)

    def mock_execute(sql, *args):
        if "INSERT INTO memory_entities_vec" in sql:
            raise Exception("SIMULATED INSERT FAILURE")
        m = MagicMock()
        m.fetchone.return_value = ("eid-123",)
        return m

    mock_conn.execute.side_effect = mock_execute

    eid = insert_entity_with_embedding(mock_conn, "Failure", "concept", [0.1] * 768)
    assert eid == "eid-123"


def test_find_similar_entity_default_threshold():
    with patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True):
        mock_conn = MagicMock()
        # Stage 1 miss
        mock_conn.execute.return_value.fetchone.return_value = None
        # Stage 2 KNN hit
        mock_conn.execute.return_value.fetchall.return_value = [(1, 0.0)]
        # Stage 2 Entity lookup
        mock_conn.execute.return_value.fetchone.side_effect = [None, ("eid-123",)]

        v = [0.1] * 768
        eid = find_similar_entity(mock_conn, "Similar", "concept", v, threshold=None)
        assert eid == "eid-123"


def test_find_similar_entity_no_results():
    with patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True):
        mock_conn = MagicMock()
        # Stage 1 miss
        mock_conn.execute.return_value.fetchone.return_value = None
        # Stage 2 KNN miss
        mock_conn.execute.return_value.fetchall.return_value = []

        v = [0.1] * 768
        eid = find_similar_entity(mock_conn, "Similar", "concept", v)
        assert eid is None


def test_find_similar_entity_dict_rows():
    # Test lines 116, 119, 131 where rows have .keys() (e.g. Row objects)
    with patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True):
        mock_conn = MagicMock()

        # Stage 1 miss
        mock_conn.execute.return_value.fetchone.return_value = None

        # Stage 2 KNN hit with dict-like row
        knn_row = MagicMock()
        knn_row.keys.return_value = ["rowid", "distance"]
        knn_row.__getitem__.side_effect = lambda k: 1 if k == "rowid" else 0.1
        mock_conn.execute.return_value.fetchall.return_value = [knn_row]

        # Stage 2 Entity lookup with dict-like row
        ent_row = MagicMock()
        ent_row.keys.return_value = ["id"]
        ent_row.__getitem__.return_value = "eid-456"

        mock_conn.execute.return_value.fetchone.side_effect = [
            None,  # Stage 1 miss
            ent_row,  # Stage 2 hit
        ]

        v = [0.1] * 768
        eid = find_similar_entity(mock_conn, "Similar", "concept", v)
        assert eid == "eid-456"
