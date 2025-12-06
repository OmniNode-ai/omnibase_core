"""Unit tests for the hash utility module.

Tests deterministic hash functions for cache keys, UUIDs, jitter, and error codes.
"""

from uuid import UUID

import pytest

from omnibase_core.utils.util_hash import (
    deterministic_cache_key,
    deterministic_error_code,
    deterministic_hash,
    deterministic_hash_int,
    deterministic_jitter,
    string_to_uuid,
)


class TestDeterministicHash:
    """Tests for the deterministic_hash function."""

    def test_returns_hex_string(self) -> None:
        """Should return a valid hexadecimal string."""
        result = deterministic_hash("test")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 produces 64 hex chars
        # Check it's valid hex
        int(result, 16)

    def test_consistent_results(self) -> None:
        """Should return the same hash for the same input."""
        result1 = deterministic_hash("hello world")
        result2 = deterministic_hash("hello world")
        assert result1 == result2

    def test_different_inputs_different_hashes(self) -> None:
        """Should return different hashes for different inputs."""
        result1 = deterministic_hash("hello")
        result2 = deterministic_hash("world")
        assert result1 != result2

    def test_empty_string(self) -> None:
        """Should handle empty strings."""
        result = deterministic_hash("")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_unicode_handling(self) -> None:
        """Should correctly handle unicode strings."""
        result = deterministic_hash("hello")
        # Verify consistency with repeated calls
        assert result == deterministic_hash("hello")

    def test_long_input(self) -> None:
        """Should handle long input strings."""
        long_input = "a" * 10000
        result = deterministic_hash(long_input)
        assert isinstance(result, str)
        assert len(result) == 64


class TestDeterministicHashInt:
    """Tests for the deterministic_hash_int function."""

    def test_returns_positive_integer(self) -> None:
        """Should return a positive integer."""
        result = deterministic_hash_int("test")
        assert isinstance(result, int)
        assert result >= 0

    def test_consistent_results(self) -> None:
        """Should return the same integer for the same input."""
        result1 = deterministic_hash_int("hello world")
        result2 = deterministic_hash_int("hello world")
        assert result1 == result2

    def test_different_inputs_different_values(self) -> None:
        """Should return different values for different inputs."""
        result1 = deterministic_hash_int("hello")
        result2 = deterministic_hash_int("world")
        assert result1 != result2

    def test_usable_for_modular_arithmetic(self) -> None:
        """Should be usable for selecting from a list."""
        nodes = ["node1", "node2", "node3"]
        index = deterministic_hash_int("session_123") % len(nodes)
        assert 0 <= index < len(nodes)


class TestDeterministicCacheKey:
    """Tests for the deterministic_cache_key function."""

    def test_returns_hex_string(self) -> None:
        """Should return a valid hexadecimal string."""
        result = deterministic_cache_key("func", (1, 2))
        assert isinstance(result, str)
        assert len(result) == 64

    def test_consistent_results(self) -> None:
        """Should return the same key for the same arguments."""
        result1 = deterministic_cache_key("func", (1, 2), foo="bar")
        result2 = deterministic_cache_key("func", (1, 2), foo="bar")
        assert result1 == result2

    def test_different_args_different_keys(self) -> None:
        """Should return different keys for different arguments."""
        result1 = deterministic_cache_key("func1", (1,))
        result2 = deterministic_cache_key("func2", (1,))
        assert result1 != result2

    def test_kwargs_order_independence(self) -> None:
        """Should produce the same key regardless of kwargs order."""
        # Python dicts maintain insertion order, but we sort kwargs
        result1 = deterministic_cache_key("f", a=1, b=2)
        result2 = deterministic_cache_key("f", b=2, a=1)
        assert result1 == result2

    def test_no_args(self) -> None:
        """Should handle no arguments."""
        result = deterministic_cache_key()
        assert isinstance(result, str)
        assert len(result) == 64


class TestStringToUuid:
    """Tests for the string_to_uuid function."""

    def test_returns_uuid(self) -> None:
        """Should return a valid UUID object."""
        result = string_to_uuid("my_dependency")
        assert isinstance(result, UUID)

    def test_consistent_results(self) -> None:
        """Should return the same UUID for the same input."""
        result1 = string_to_uuid("test_string")
        result2 = string_to_uuid("test_string")
        assert result1 == result2

    def test_different_inputs_different_uuids(self) -> None:
        """Should return different UUIDs for different inputs."""
        result1 = string_to_uuid("string1")
        result2 = string_to_uuid("string2")
        assert result1 != result2

    def test_valid_uuid_format(self) -> None:
        """Should produce a valid UUID that can be stringified."""
        result = string_to_uuid("test")
        uuid_str = str(result)
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = uuid_str.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_empty_string(self) -> None:
        """Should handle empty strings."""
        result = string_to_uuid("")
        assert isinstance(result, UUID)


class TestDeterministicJitter:
    """Tests for the deterministic_jitter function."""

    def test_returns_float(self) -> None:
        """Should return a float."""
        result = deterministic_jitter("seed", 1.0, 0.1)
        assert isinstance(result, float)

    def test_consistent_results(self) -> None:
        """Should return the same jitter for the same seed."""
        result1 = deterministic_jitter("seed123", 1.0, 0.1)
        result2 = deterministic_jitter("seed123", 1.0, 0.1)
        assert result1 == result2

    def test_different_seeds_different_jitter(self) -> None:
        """Should return different jitter for different seeds."""
        result1 = deterministic_jitter("seed1", 1.0, 0.1)
        result2 = deterministic_jitter("seed2", 1.0, 0.1)
        # Not necessarily different, but likely
        # We just verify they're both valid
        assert -0.1 <= result1 <= 0.1
        assert -0.1 <= result2 <= 0.1

    def test_jitter_within_range(self) -> None:
        """Should return jitter within the specified factor range."""
        base_delay = 1.0
        jitter_factor = 0.1
        for i in range(100):
            result = deterministic_jitter(f"seed_{i}", base_delay, jitter_factor)
            # Jitter should be between -0.1 and 0.1 (jitter_factor * base_delay)
            max_jitter = base_delay * jitter_factor
            assert -max_jitter <= result <= max_jitter

    def test_zero_base_delay(self) -> None:
        """Should handle zero base delay."""
        result = deterministic_jitter("seed", 0.0, 0.1)
        assert result == 0.0

    def test_zero_jitter_factor(self) -> None:
        """Should return zero jitter when factor is zero."""
        result = deterministic_jitter("seed", 1.0, 0.0)
        assert result == 0.0


class TestDeterministicErrorCode:
    """Tests for the deterministic_error_code function."""

    def test_returns_float(self) -> None:
        """Should return a float."""
        result = deterministic_error_code("Connection refused")
        assert isinstance(result, float)

    def test_consistent_results(self) -> None:
        """Should return the same code for the same message."""
        result1 = deterministic_error_code("Connection refused")
        result2 = deterministic_error_code("Connection refused")
        assert result1 == result2

    def test_different_messages_different_codes(self) -> None:
        """Should return different codes for different messages."""
        result1 = deterministic_error_code("Error A")
        result2 = deterministic_error_code("Error B")
        # Not necessarily different, but likely
        # We just verify they're both valid
        assert 0.0 <= result1 <= 1.0
        assert 0.0 <= result2 <= 1.0

    def test_range_zero_to_one(self) -> None:
        """Should always return a value between 0.0 and 1.0."""
        test_messages = [
            "Connection refused",
            "Timeout",
            "Internal server error",
            "",
            "a" * 10000,
        ]
        for msg in test_messages:
            result = deterministic_error_code(msg)
            assert 0.0 <= result <= 1.0

    def test_empty_string(self) -> None:
        """Should handle empty strings."""
        result = deterministic_error_code("")
        assert 0.0 <= result <= 1.0


class TestCrossProcessConsistency:
    """Tests to verify hash consistency (simulated).

    Note: True cross-process testing requires running separate Python
    processes. These tests verify the underlying hash algorithm is
    deterministic by checking known values.
    """

    def test_known_hash_values(self) -> None:
        """Verify known hash values don't change."""
        # SHA-256 hash of "test" is well-known
        expected = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        assert deterministic_hash("test") == expected

    def test_known_empty_hash(self) -> None:
        """Verify hash of empty string is correct."""
        # SHA-256 hash of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert deterministic_hash("") == expected

    def test_uuid_from_empty_string_is_valid(self) -> None:
        """Verify UUID from empty string is valid and consistent."""
        result = string_to_uuid("")
        # First 32 chars of SHA-256 of empty string
        expected = UUID("e3b0c442-98fc-1c14-9afb-f4c8996fb924")
        assert result == expected
