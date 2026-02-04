"""Unit tests for Blake3 hashing utilities."""

from __future__ import annotations

import pytest

from omnibase_core.crypto.crypto_blake3_hasher import hash_bytes, hash_canonical_json


@pytest.mark.unit
class TestHashBytes:
    """Tests for hash_bytes function."""

    def test_hash_bytes_returns_hex_string(self) -> None:
        """hash_bytes returns a hex-encoded string."""
        result = hash_bytes(b"hello world")
        assert isinstance(result, str)
        assert len(result) == 64  # Blake3 produces 256-bit (32 bytes = 64 hex chars)

    def test_hash_bytes_deterministic(self) -> None:
        """Same input always produces same hash."""
        data = b"test data"
        hash1 = hash_bytes(data)
        hash2 = hash_bytes(data)
        assert hash1 == hash2

    def test_hash_bytes_different_inputs_different_hashes(self) -> None:
        """Different inputs produce different hashes."""
        hash1 = hash_bytes(b"input1")
        hash2 = hash_bytes(b"input2")
        assert hash1 != hash2

    def test_hash_bytes_empty_input(self) -> None:
        """Empty bytes can be hashed."""
        result = hash_bytes(b"")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_bytes_large_input(self) -> None:
        """Large inputs can be hashed."""
        large_data = b"x" * (1024 * 1024)  # 1 MB
        result = hash_bytes(large_data)
        assert isinstance(result, str)
        assert len(result) == 64


@pytest.mark.unit
class TestHashCanonicalJson:
    """Tests for hash_canonical_json function."""

    def test_hash_canonical_json_returns_hex_string(self) -> None:
        """hash_canonical_json returns a hex-encoded string."""
        result = hash_canonical_json({"key": "value"})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_canonical_json_deterministic(self) -> None:
        """Same dict always produces same hash."""
        data = {"a": 1, "b": 2}
        hash1 = hash_canonical_json(data)
        hash2 = hash_canonical_json(data)
        assert hash1 == hash2

    def test_hash_canonical_json_key_order_independent(self) -> None:
        """Key order doesn't affect hash (canonical serialization)."""
        # Python dicts maintain insertion order, but canonical JSON sorts keys
        dict1 = {"b": 2, "a": 1}
        dict2 = {"a": 1, "b": 2}
        hash1 = hash_canonical_json(dict1)
        hash2 = hash_canonical_json(dict2)
        assert hash1 == hash2

    def test_hash_canonical_json_nested_dicts(self) -> None:
        """Nested dicts are handled correctly."""
        data = {"outer": {"inner": {"deep": "value"}}}
        result = hash_canonical_json(data)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_canonical_json_with_lists(self) -> None:
        """Lists in dicts are handled correctly."""
        data = {"items": [1, 2, 3], "name": "test"}
        result = hash_canonical_json(data)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_canonical_json_empty_dict(self) -> None:
        """Empty dict can be hashed."""
        result = hash_canonical_json({})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_canonical_json_different_dicts_different_hashes(self) -> None:
        """Different dicts produce different hashes."""
        hash1 = hash_canonical_json({"a": 1})
        hash2 = hash_canonical_json({"a": 2})
        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
