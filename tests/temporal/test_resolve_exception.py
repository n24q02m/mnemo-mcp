import struct
from unittest.mock import MagicMock, patch

from mnemo_mcp.temporal.resolve import (
    _DEFAULT_EMBEDDING_DIMS,
    _DEFAULT_THRESHOLD,
    _resolve_dims,
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


def test_resolve_threshold_exception_handling(monkeypatch):
    monkeypatch.setenv("TEMPORAL_ENTITY_RESOLUTION_THRESHOLD", "invalid")
    with patch("mnemo_mcp.temporal.resolve.logger") as mock_logger:
        res = _resolve_threshold()
        assert res == _DEFAULT_THRESHOLD
        mock_logger.warning.assert_called()
        args, _ = mock_logger.warning.call_args
        assert "is not a float" in args[0]


def test_resolve_dims_exception_handling():
    # We patch the import location within the function
    with patch("mnemo_mcp.temporal.resolve.settings", create=True) as mock_settings:
        # If the function does 'from mnemo_mcp.config import settings',
        # it might not use the patch if we patch it in the wrong place.
        # But if we patch 'mnemo_mcp.config.settings' and it's already imported elsewhere...
        pass

    # Let's try patching where it is used.
    with patch("mnemo_mcp.config.settings") as mock_settings:
        mock_settings.resolve_embedding_dims.side_effect = Exception("config error")
        assert _resolve_dims() == _DEFAULT_EMBEDDING_DIMS


def test_serialize_padding():
    # _resolve_dims returns 768 by default
    vec = [1.0, 2.0]
    res = _serialize(vec)
    assert len(res) == _DEFAULT_EMBEDDING_DIMS * 4
    # Unpack to verify padding
    unpacked = struct.unpack(f"{_DEFAULT_EMBEDDING_DIMS}f", res)
    assert unpacked[0] == 1.0
    assert unpacked[1] == 2.0
    assert all(v == 0.0 for v in unpacked[2:])
