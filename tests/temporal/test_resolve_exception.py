import struct
from unittest.mock import MagicMock, patch

import pytest

from mnemo_mcp.temporal.resolve import (
    _resolve_threshold,
    _serialize,
    find_similar_entity,
    insert_entity_with_embedding,
)


def test_find_similar_entity_exception_handling():
    conn = MagicMock()
    # Force _vec_table_exists to True so it proceeds to KNN
    with (
        patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True),
        patch("mnemo_mcp.temporal.resolve.logger") as mock_logger,
    ):

        def side_effect(query, *args):
            if "memory_entities_vec" in query:
                raise Exception("KNN error")
            mock_res = MagicMock()
            mock_res.fetchone.return_value = None
            return mock_res

        conn.execute.side_effect = side_effect

        res = find_similar_entity(conn, "name", "type", [0.1] * 768)

        assert res is None
        mock_logger.debug.assert_called_with(
            "temporal.resolve: vec KNN failed (non-blocking): KNN error"
        )


def test_insert_entity_with_embedding_exception_handling():
    conn = MagicMock()
    # Force _vec_table_exists to True
    with (
        patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True),
        patch("mnemo_mcp.temporal.resolve.logger") as mock_logger,
    ):

        def side_effect(query, *args):
            if "INSERT INTO memory_entities_vec" in query:
                raise Exception("Insert error")
            mock_res = MagicMock()
            if "SELECT id FROM memory_entities" in query:
                mock_res.fetchone.return_value = ["some-id"]
            elif "SELECT rowid FROM memory_entities" in query:
                mock_res.fetchone.return_value = [123]
            return mock_res

        conn.execute.side_effect = side_effect

        res = insert_entity_with_embedding(conn, "name", "type", [0.1] * 768)

        assert res == "some-id"
        mock_logger.debug.assert_called_with(
            "temporal.resolve: embedding insert failed (non-blocking): Insert error"
        )


def test_serialize_short_vector():
    vec = [0.1, 0.2]
    res = _serialize(vec)
    assert len(res) == 768 * 4
    unpacked = struct.unpack("768f", res)
    assert unpacked[0] == pytest.approx(0.1)
    assert unpacked[1] == pytest.approx(0.2)
    assert all(v == 0.0 for v in unpacked[2:])


def test_serialize_long_vector():
    vec = [0.1] * 1000
    res = _serialize(vec)
    assert len(res) == 768 * 4
    unpacked = struct.unpack("768f", res)
    assert len(unpacked) == 768


def test_insert_entity_with_embedding_no_rowid():
    conn = MagicMock()
    # Mocking refetch of id to succeed
    actual_mock = MagicMock()
    actual_mock.__getitem__.side_effect = lambda x: (
        "some-id" if x == 0 or x == "id" else None
    )
    actual_mock.keys.return_value = ["id"]

    # Mocking refetch of rowid to return None
    def side_effect(query, *args):
        mock_res = MagicMock()
        if "SELECT id FROM memory_entities" in query:
            mock_res.fetchone.return_value = actual_mock
            return mock_res
        if "SELECT rowid FROM memory_entities" in query:
            mock_res.fetchone.return_value = None
            return mock_res
        return mock_res

    conn.execute.side_effect = side_effect

    with patch("mnemo_mcp.temporal.resolve._vec_table_exists", return_value=True):
        res = insert_entity_with_embedding(conn, "name", "type", [0.1] * 768)
        assert res == "some-id"
        # Ensure it didn't try to DELETE or INSERT into vec table
        for call in conn.execute.call_args_list:
            query = call[0][0]
            assert "DELETE FROM memory_entities_vec" not in query
            assert "INSERT INTO memory_entities_vec" not in query


def test_resolve_threshold_invalid_env(monkeypatch):
    monkeypatch.setenv("TEMPORAL_ENTITY_RESOLUTION_THRESHOLD", "not-a-float")
    with patch("mnemo_mcp.temporal.resolve.logger") as mock_logger:
        val = _resolve_threshold()
        assert val == 0.85
        mock_logger.warning.assert_called()
