"""Tests for internal DB utilities."""

import struct

from mnemo_mcp.db import _serialize_f32


class TestSerializeF32:
    def test_basic_serialization(self):
        vec = [1.0, 2.0, 3.0]
        result = _serialize_f32(vec)
        assert isinstance(result, bytes)
        assert len(result) == 12  # 3 floats * 4 bytes each
        unpacked = struct.unpack("3f", result)
        assert unpacked == (1.0, 2.0, 3.0)

    def test_empty_list(self):
        result = _serialize_f32([])
        assert result == b""

    def test_integers(self):
        """Integers should be serialized as floats."""
        vec = [1, 2, 3]
        result = _serialize_f32(vec)
        unpacked = struct.unpack("3f", result)
        assert unpacked == (1.0, 2.0, 3.0)

    def test_single_value(self):
        vec = [3.14]
        result = _serialize_f32(vec)
        assert len(result) == 4
        unpacked = struct.unpack("1f", result)
        assert abs(unpacked[0] - 3.14) < 1e-6

    def test_negative_values(self):
        vec = [-1.0, -0.5]
        result = _serialize_f32(vec)
        unpacked = struct.unpack("2f", result)
        assert unpacked == (-1.0, -0.5)

    def test_large_values(self):
        vec = [1e10, -1e10]
        result = _serialize_f32(vec)
        unpacked = struct.unpack("2f", result)
        assert unpacked == (1e10, -1e10)

    def test_roundtrip(self):
        """Verify roundtrip conversion."""
        vec = [0.1, 0.2, 0.3, -0.4, 100.0]
        result = _serialize_f32(vec)
        unpacked = list(struct.unpack(f"{len(vec)}f", result))
        # Use approx for float comparison
        for v1, v2 in zip(vec, unpacked, strict=True):
            assert abs(v1 - v2) < 1e-6
