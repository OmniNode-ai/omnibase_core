# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for EnumHashAlgorithm."""

import pytest

from omnibase_core.enums.enum_hash_algorithm import EnumHashAlgorithm


@pytest.mark.unit
class TestEnumHashAlgorithm:
    """Tests for EnumHashAlgorithm enum."""

    # --- Enum value tests ---

    def test_sha256_value_is_sha256_string(self) -> None:
        """Test that SHA256 enum value is 'sha256'."""
        assert EnumHashAlgorithm.SHA256.value == "sha256"

    def test_enum_inherits_from_str(self) -> None:
        """Test that enum inherits from str for direct string comparison."""
        assert isinstance(EnumHashAlgorithm.SHA256, str)
        assert EnumHashAlgorithm.SHA256 == "sha256"

    # --- expected_length tests ---

    def test_sha256_expected_length_is_64(self) -> None:
        """Test that SHA256 expected_length returns 64."""
        assert EnumHashAlgorithm.SHA256.expected_length == 64

    def test_expected_length_returns_integer(self) -> None:
        """Test that expected_length property returns an integer type."""
        result = EnumHashAlgorithm.SHA256.expected_length
        assert isinstance(result, int)

    # --- validate_hash tests - valid cases ---

    def test_validate_hash_accepts_valid_sha256(self) -> None:
        """Test that validate_hash accepts a valid SHA256 hash."""
        valid_hash = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        assert EnumHashAlgorithm.SHA256.validate_hash(valid_hash) is True

    def test_validate_hash_accepts_all_zeros(self) -> None:
        """Test that validate_hash accepts a hash of all zeros."""
        all_zeros = "0" * 64
        assert EnumHashAlgorithm.SHA256.validate_hash(all_zeros) is True

    def test_validate_hash_accepts_all_hex_chars(self) -> None:
        """Test that validate_hash accepts all valid lowercase hex characters."""
        # Build a hash using all valid hex chars: 0-9 and a-f
        hex_chars_hash = "0123456789abcdef" * 4  # 16 * 4 = 64 chars
        assert EnumHashAlgorithm.SHA256.validate_hash(hex_chars_hash) is True

    # --- validate_hash tests - invalid cases ---

    def test_validate_hash_rejects_uppercase(self) -> None:
        """Test that validate_hash rejects uppercase hex characters."""
        uppercase_hash = "A" * 64
        assert EnumHashAlgorithm.SHA256.validate_hash(uppercase_hash) is False

    def test_validate_hash_rejects_mixed_case(self) -> None:
        """Test that validate_hash rejects mixed case hex characters."""
        mixed_case = "aAbBcCdDeEfF" + "0" * 52  # 64 chars total
        assert EnumHashAlgorithm.SHA256.validate_hash(mixed_case) is False

    def test_validate_hash_rejects_too_short(self) -> None:
        """Test that validate_hash rejects a hash that is too short."""
        short_hash = "a" * 63
        assert EnumHashAlgorithm.SHA256.validate_hash(short_hash) is False

    def test_validate_hash_rejects_too_long(self) -> None:
        """Test that validate_hash rejects a hash that is too long."""
        long_hash = "a" * 65
        assert EnumHashAlgorithm.SHA256.validate_hash(long_hash) is False

    def test_validate_hash_rejects_non_hex_chars(self) -> None:
        """Test that validate_hash rejects non-hex characters."""
        # 'g' is not a valid hex character
        invalid_hash = "g" * 64
        assert EnumHashAlgorithm.SHA256.validate_hash(invalid_hash) is False

    def test_validate_hash_rejects_special_chars(self) -> None:
        """Test that validate_hash rejects special characters."""
        special_hash = "!" + "a" * 63
        assert EnumHashAlgorithm.SHA256.validate_hash(special_hash) is False

    def test_validate_hash_rejects_empty_string(self) -> None:
        """Test that validate_hash rejects an empty string."""
        assert EnumHashAlgorithm.SHA256.validate_hash("") is False

    def test_validate_hash_rejects_whitespace(self) -> None:
        """Test that validate_hash rejects strings with whitespace."""
        whitespace_hash = " " + "a" * 63
        assert EnumHashAlgorithm.SHA256.validate_hash(whitespace_hash) is False

    # --- Edge case tests ---

    def test_validate_hash_exact_length_boundary(self) -> None:
        """Test validation at exact length boundaries."""
        # Exactly 64 chars - valid
        exactly_64 = "a" * 64
        assert EnumHashAlgorithm.SHA256.validate_hash(exactly_64) is True

        # 63 chars - invalid
        exactly_63 = "a" * 63
        assert EnumHashAlgorithm.SHA256.validate_hash(exactly_63) is False

        # 65 chars - invalid
        exactly_65 = "a" * 65
        assert EnumHashAlgorithm.SHA256.validate_hash(exactly_65) is False
