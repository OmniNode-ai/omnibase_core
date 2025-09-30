"""
Unit tests for EnumCliStatus.

Tests all aspects of the CLI status enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Edge cases and error conditions
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_cli_status import EnumCliStatus


class TestEnumCliStatus:
    """Test cases for EnumCliStatus."""

    def test_enum_inherits_from_str_and_enum(self):
        """Test that EnumCliStatus properly inherits from str and Enum."""
        assert issubclass(EnumCliStatus, str)
        assert issubclass(EnumCliStatus, Enum)

    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "SUCCESS",
            "FAILED",
            "WARNING",
            "RUNNING",
            "CANCELLED",
            "TIMEOUT",
        ]

        for value in expected_values:
            assert hasattr(EnumCliStatus, value), f"Missing enum value: {value}"

    def test_enum_string_values(self):
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumCliStatus.SUCCESS: "success",
            EnumCliStatus.FAILED: "failed",
            EnumCliStatus.WARNING: "warning",
            EnumCliStatus.RUNNING: "running",
            EnumCliStatus.CANCELLED: "cancelled",
            EnumCliStatus.TIMEOUT: "timeout",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_can_be_created_from_string(self):
        """Test that enum members can be created from string values."""
        assert EnumCliStatus("success") == EnumCliStatus.SUCCESS
        assert EnumCliStatus("failed") == EnumCliStatus.FAILED
        assert EnumCliStatus("warning") == EnumCliStatus.WARNING
        assert EnumCliStatus("running") == EnumCliStatus.RUNNING
        assert EnumCliStatus("cancelled") == EnumCliStatus.CANCELLED
        assert EnumCliStatus("timeout") == EnumCliStatus.TIMEOUT

    def test_enum_string_comparison(self):
        """Test that enum members can be compared with strings."""
        assert EnumCliStatus.SUCCESS == "success"
        assert EnumCliStatus.FAILED == "failed"
        assert EnumCliStatus.WARNING == "warning"
        assert EnumCliStatus.RUNNING == "running"
        assert EnumCliStatus.CANCELLED == "cancelled"
        assert EnumCliStatus.TIMEOUT == "timeout"

    def test_enum_member_count(self):
        """Test that the enum has the expected number of members."""
        expected_count = 6
        actual_count = len(list(EnumCliStatus))
        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} members, got {actual_count}"

    def test_enum_member_uniqueness(self):
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumCliStatus]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        expected_values = {
            "success",
            "failed",
            "warning",
            "running",
            "cancelled",
            "timeout",
        }
        actual_values = {member.value for member in EnumCliStatus}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self):
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumCliStatus("invalid_status")

    def test_enum_in_operator(self):
        """Test that 'in' operator works with enum."""
        assert EnumCliStatus.SUCCESS in EnumCliStatus
        assert EnumCliStatus.FAILED in EnumCliStatus

        # Test that strings work with member values
        success_member = EnumCliStatus.SUCCESS
        assert success_member.value == "success"

    def test_enum_hash_consistency(self):
        """Test that enum members are hashable and consistent."""
        status_set = {EnumCliStatus.SUCCESS, EnumCliStatus.FAILED}
        assert len(status_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumCliStatus.SUCCESS) == hash(EnumCliStatus.SUCCESS)

    def test_enum_repr(self):
        """Test that enum members have proper string representation."""
        assert repr(EnumCliStatus.SUCCESS) == "<EnumCliStatus.SUCCESS: 'success'>"
        assert repr(EnumCliStatus.FAILED) == "<EnumCliStatus.FAILED: 'failed'>"

    def test_enum_bool_evaluation(self):
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumCliStatus:
            assert bool(member) is True

    def test_enum_serialization_json_compatible(self):
        """Test that enum values are JSON serializable."""
        import json

        for member in EnumCliStatus:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumCliStatus(deserialized)
            assert reconstructed == member

    def test_enum_case_sensitivity(self):
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumCliStatus("SUCCESS")  # Should be "success"

        with pytest.raises(ValueError):
            EnumCliStatus("Success")  # Should be "success"

    def test_enum_with_pydantic_compatibility(self):
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumCliStatus

        # Test valid values
        model = TestModel(status=EnumCliStatus.SUCCESS)
        assert model.status == EnumCliStatus.SUCCESS

        # Test string initialization
        model = TestModel(status="failed")
        assert model.status == EnumCliStatus.FAILED

        # Test serialization
        data = model.model_dump()
        assert data["status"] == "failed"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.status == EnumCliStatus.FAILED

    def test_enum_equality_and_identity(self):
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumCliStatus.SUCCESS is EnumCliStatus.SUCCESS

        # Different enum members should not be identical
        assert EnumCliStatus.SUCCESS is not EnumCliStatus.FAILED

        # Equality with strings should work
        assert EnumCliStatus.SUCCESS == "success"
        assert EnumCliStatus.SUCCESS != "failed"

    def test_enum_ordering_behavior(self):
        """Test that enum members support ordering (inherits from str)."""
        # Since EnumCliStatus(str, Enum), it supports string ordering
        result1 = EnumCliStatus.SUCCESS < EnumCliStatus.FAILED
        result2 = EnumCliStatus.SUCCESS > EnumCliStatus.FAILED

        # The results depend on string comparison of the values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)


class TestEnumCliStatusEdgeCases:
    """Test edge cases and error conditions for EnumCliStatus."""

    def test_enum_with_none_value(self):
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumCliStatus(None)

    def test_enum_with_empty_string(self):
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumCliStatus("")

    def test_enum_with_whitespace(self):
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumCliStatus(" success ")

        with pytest.raises(ValueError):
            EnumCliStatus("success ")

    def test_enum_pickling(self):
        """Test that enum members can be pickled and unpickled."""
        import pickle

        for member in EnumCliStatus:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self):
        """Test enum behavior with copy operations."""
        import copy

        status = EnumCliStatus.SUCCESS

        # Shallow copy should return the same object
        shallow_copy = copy.copy(status)
        assert shallow_copy is status

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(status)
        assert deep_copy is status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
