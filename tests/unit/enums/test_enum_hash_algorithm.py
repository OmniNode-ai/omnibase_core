# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for EnumHashAlgorithm.

Tests all aspects of the hash algorithm enumeration including:
- SHA256 specific tests (primary focus for handler packaging v1)
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Hash validation functionality
- Edge cases and error conditions
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_hash_algorithm import EnumHashAlgorithm


@pytest.mark.unit
class TestEnumHashAlgorithm:
    """Tests for EnumHashAlgorithm enum."""

    # -------------------------------------------------------------------------
    # SHA256 Specific Tests (Primary Focus)
    # -------------------------------------------------------------------------

    def test_sha256_exists(self) -> None:
        """Test that SHA256 enum member exists."""
        assert hasattr(EnumHashAlgorithm, "SHA256")
        assert EnumHashAlgorithm.SHA256 is not None

    def test_sha256_value_is_sha256_string(self) -> None:
        """Test that SHA256 enum value is 'sha256'."""
        assert EnumHashAlgorithm.SHA256.value == "sha256"

    def test_sha256_is_string_enum(self) -> None:
        """Test that SHA256 inherits from str and Enum."""
        assert isinstance(EnumHashAlgorithm.SHA256, str)
        assert isinstance(EnumHashAlgorithm.SHA256, Enum)

    def test_sha256_can_be_created_from_string(self) -> None:
        """Test that SHA256 can be created from its string value."""
        created = EnumHashAlgorithm("sha256")
        assert created == EnumHashAlgorithm.SHA256
        assert created is EnumHashAlgorithm.SHA256

    def test_sha256_case_sensitivity(self) -> None:
        """Test that SHA256 string value is case sensitive."""
        # Must use lowercase "sha256"
        with pytest.raises(ValueError):
            EnumHashAlgorithm("SHA256")  # Uppercase should fail

        with pytest.raises(ValueError):
            EnumHashAlgorithm("Sha256")  # Mixed case should fail

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

    # -------------------------------------------------------------------------
    # Real-world hash validation tests
    # -------------------------------------------------------------------------

    def test_validate_hash_real_sha256_examples(self) -> None:
        """Test with real SHA256 hash examples from known inputs."""
        # SHA256("hello world") - actual hash value
        hello_world_hash = (
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )
        assert EnumHashAlgorithm.SHA256.validate_hash(hello_world_hash) is True

        # SHA256 of empty string
        empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert EnumHashAlgorithm.SHA256.validate_hash(empty_hash) is True

        # SHA256("test")
        test_hash = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        assert EnumHashAlgorithm.SHA256.validate_hash(test_hash) is True

    def test_validate_hash_all_numeric(self) -> None:
        """Test that all-numeric hashes are valid."""
        numeric_hash = (
            "1234567890123456789012345678901234567890123456789012345678901234"
        )
        assert EnumHashAlgorithm.SHA256.validate_hash(numeric_hash) is True

    def test_validate_hash_all_letters(self) -> None:
        """Test that all-letter (a-f) hashes are valid."""
        letter_hash = "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        assert EnumHashAlgorithm.SHA256.validate_hash(letter_hash) is True

    def test_validate_hash_rejects_newline(self) -> None:
        """Test that hashes with newlines are rejected."""
        hash_with_newline = "a" * 63 + "\n"
        assert EnumHashAlgorithm.SHA256.validate_hash(hash_with_newline) is False

    def test_validate_hash_rejects_trailing_space(self) -> None:
        """Test that hashes with trailing space are rejected."""
        hash_with_space = "a" * 63 + " "
        assert EnumHashAlgorithm.SHA256.validate_hash(hash_with_space) is False

    def test_validate_hash_rejects_leading_newline(self) -> None:
        """Test that hashes with leading newline are rejected."""
        hash_with_newline = "\n" + "a" * 63
        assert EnumHashAlgorithm.SHA256.validate_hash(hash_with_newline) is False

    def test_validate_hash_rejects_unicode(self) -> None:
        """Test that hashes with unicode characters are rejected."""
        # Unicode that looks like a hex char
        unicode_hash = "a" * 63 + "\u0061"  # unicode 'a'
        # This should work since it's actually 'a'
        assert EnumHashAlgorithm.SHA256.validate_hash(unicode_hash) is True

        # But non-ascii unicode should fail
        unicode_hash_invalid = "a" * 63 + "\u00e1"  # 'á' - not a hex char
        assert EnumHashAlgorithm.SHA256.validate_hash(unicode_hash_invalid) is False

    def test_validate_hash_rejects_null_byte(self) -> None:
        """Test that hashes with null bytes are rejected."""
        hash_with_null = "a" * 63 + "\x00"
        assert EnumHashAlgorithm.SHA256.validate_hash(hash_with_null) is False

    # -------------------------------------------------------------------------
    # General Enum Tests
    # -------------------------------------------------------------------------

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumHashAlgorithm properly inherits from str and Enum."""
        assert issubclass(EnumHashAlgorithm, str)
        assert issubclass(EnumHashAlgorithm, Enum)

    def test_all_values_are_strings(self) -> None:
        """Test that all enum values are strings."""
        for member in EnumHashAlgorithm:
            assert isinstance(member.value, str)
            assert isinstance(member, str)

    def test_enum_member_count(self) -> None:
        """Test that the enum has exactly 1 member (SHA256 only in v1)."""
        expected_count = 1
        actual_count = len(list(EnumHashAlgorithm))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_all_expected_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        expected_members = ["SHA256"]
        for member_name in expected_members:
            assert hasattr(EnumHashAlgorithm, member_name), (
                f"Missing enum member: {member_name}"
            )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumHashAlgorithm]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        expected_values = {"sha256"}
        actual_values = {member.value for member in EnumHashAlgorithm}
        assert actual_values == expected_values

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        assert EnumHashAlgorithm("sha256") == EnumHashAlgorithm.SHA256

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert EnumHashAlgorithm.SHA256 == "sha256"
        assert EnumHashAlgorithm.SHA256 != "SHA256"  # case sensitive

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumHashAlgorithm("invalid")

        with pytest.raises(ValueError):
            EnumHashAlgorithm("md5")

        with pytest.raises(ValueError):
            EnumHashAlgorithm("sha512")  # Not supported in v1

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        algo_set = {EnumHashAlgorithm.SHA256}
        assert len(algo_set) == 1

        # Same enum members should have same hash
        assert hash(EnumHashAlgorithm.SHA256) == hash(EnumHashAlgorithm.SHA256)

    def test_enum_repr(self) -> None:
        """Test that enum members have proper string representation."""
        assert repr(EnumHashAlgorithm.SHA256) == "<EnumHashAlgorithm.SHA256: 'sha256'>"

    def test_enum_bool_evaluation(self) -> None:
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumHashAlgorithm:
            assert bool(member) is True

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumHashAlgorithm:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumHashAlgorithm(deserialized)
            assert reconstructed == member

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumHashAlgorithm.SHA256 is EnumHashAlgorithm.SHA256

        # Equality with strings should work
        assert EnumHashAlgorithm.SHA256 == "sha256"
        assert EnumHashAlgorithm.SHA256 != "md5"

    def test_enum_in_operator(self) -> None:
        """Test that 'in' operator works with enum."""
        assert EnumHashAlgorithm.SHA256 in EnumHashAlgorithm

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            algorithm: EnumHashAlgorithm

        # Test valid values
        model = TestModel(algorithm=EnumHashAlgorithm.SHA256)
        assert model.algorithm == EnumHashAlgorithm.SHA256

        # Test string initialization
        model = TestModel(algorithm="sha256")
        assert model.algorithm == EnumHashAlgorithm.SHA256

        # Test serialization
        data = model.model_dump()
        assert data["algorithm"] == "sha256"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.algorithm == EnumHashAlgorithm.SHA256


@pytest.mark.unit
class TestEnumHashAlgorithmEdgeCases:
    """Test edge cases and error conditions for EnumHashAlgorithm."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((TypeError, ValueError)):
            EnumHashAlgorithm(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumHashAlgorithm("")

    def test_enum_with_whitespace(self) -> None:
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumHashAlgorithm(" sha256 ")

        with pytest.raises(ValueError):
            EnumHashAlgorithm("sha256 ")

        with pytest.raises(ValueError):
            EnumHashAlgorithm(" sha256")

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumHashAlgorithm:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        algorithm = EnumHashAlgorithm.SHA256

        # Shallow copy should return the same object
        shallow_copy = copy.copy(algorithm)
        assert shallow_copy is algorithm

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(algorithm)
        assert deep_copy is algorithm

    def test_validate_hash_with_very_long_string(self) -> None:
        """Test validation with extremely long strings."""
        very_long_hash = "a" * 1000
        assert EnumHashAlgorithm.SHA256.validate_hash(very_long_hash) is False

    def test_validate_hash_with_tabs(self) -> None:
        """Test that hashes with tabs are rejected."""
        hash_with_tab = "a" * 63 + "\t"
        assert EnumHashAlgorithm.SHA256.validate_hash(hash_with_tab) is False

    def test_validate_hash_with_carriage_return(self) -> None:
        """Test that hashes with carriage returns are rejected."""
        hash_with_cr = "a" * 63 + "\r"
        assert EnumHashAlgorithm.SHA256.validate_hash(hash_with_cr) is False


@pytest.mark.unit
class TestEnumHashAlgorithmExpectedLengthProperty:
    """Test the expected_length property in detail."""

    def test_expected_length_is_immutable(self) -> None:
        """Test that expected_length returns same value on repeated calls."""
        algo = EnumHashAlgorithm.SHA256
        assert algo.expected_length == algo.expected_length
        assert algo.expected_length == 64

    def test_expected_length_matches_validate_hash(self) -> None:
        """Test that expected_length matches what validate_hash accepts."""
        algo = EnumHashAlgorithm.SHA256
        expected_len = algo.expected_length

        # Hash with expected length should be valid
        valid_hash = "a" * expected_len
        assert algo.validate_hash(valid_hash) is True

        # Hash one char shorter should be invalid
        short_hash = "a" * (expected_len - 1)
        assert algo.validate_hash(short_hash) is False

        # Hash one char longer should be invalid
        long_hash = "a" * (expected_len + 1)
        assert algo.validate_hash(long_hash) is False


@pytest.mark.unit
class TestEnumHashAlgorithmFutureCompatibility:
    """Tests to verify future algorithm additions will be caught by tests."""

    def test_current_supported_algorithms(self) -> None:
        """Document and verify current supported algorithms (v1: SHA256 only)."""
        supported = list(EnumHashAlgorithm)
        assert len(supported) == 1
        assert EnumHashAlgorithm.SHA256 in supported

    def test_algorithm_name_convention(self) -> None:
        """Test that algorithm names follow expected conventions."""
        for member in EnumHashAlgorithm:
            # Enum names should be UPPERCASE
            assert member.name.isupper(), f"{member.name} should be uppercase"
            # Values should be lowercase
            assert member.value.islower(), f"{member.value} should be lowercase"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
