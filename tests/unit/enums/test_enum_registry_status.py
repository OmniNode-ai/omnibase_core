# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumRegistryStatus.

Tests all aspects of the registry status enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
- Edge cases and error conditions
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_registry_status import EnumRegistryStatus


@pytest.mark.unit
class TestEnumRegistryStatus:
    """Test cases for EnumRegistryStatus."""

    def test_enum_inherits_from_str_and_enum(self):
        """Test that EnumRegistryStatus properly inherits from str and Enum."""
        assert issubclass(EnumRegistryStatus, str)
        assert issubclass(EnumRegistryStatus, Enum)

    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "HEALTHY",
            "DEGRADED",
            "UNAVAILABLE",
            "INITIALIZING",
            "MAINTENANCE",
        ]

        for value in expected_values:
            assert hasattr(EnumRegistryStatus, value), f"Missing enum value: {value}"

    def test_enum_string_values(self):
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumRegistryStatus.HEALTHY: "healthy",
            EnumRegistryStatus.DEGRADED: "degraded",
            EnumRegistryStatus.UNAVAILABLE: "unavailable",
            EnumRegistryStatus.INITIALIZING: "initializing",
            EnumRegistryStatus.MAINTENANCE: "maintenance",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_can_be_created_from_string(self):
        """Test that enum members can be created from string values."""
        assert EnumRegistryStatus("healthy") == EnumRegistryStatus.HEALTHY
        assert EnumRegistryStatus("degraded") == EnumRegistryStatus.DEGRADED
        assert EnumRegistryStatus("unavailable") == EnumRegistryStatus.UNAVAILABLE
        assert EnumRegistryStatus("initializing") == EnumRegistryStatus.INITIALIZING
        assert EnumRegistryStatus("maintenance") == EnumRegistryStatus.MAINTENANCE

    def test_enum_string_comparison(self):
        """Test that enum members can be compared with strings."""
        assert EnumRegistryStatus.HEALTHY == "healthy"
        assert EnumRegistryStatus.DEGRADED == "degraded"
        assert EnumRegistryStatus.UNAVAILABLE == "unavailable"
        assert EnumRegistryStatus.INITIALIZING == "initializing"
        assert EnumRegistryStatus.MAINTENANCE == "maintenance"

    def test_enum_member_count(self):
        """Test that the enum has the expected number of members."""
        expected_count = 5
        actual_count = len(list(EnumRegistryStatus))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self):
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumRegistryStatus]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        expected_values = {
            "healthy",
            "degraded",
            "unavailable",
            "initializing",
            "maintenance",
        }
        actual_values = {member.value for member in EnumRegistryStatus}
        assert actual_values == expected_values

    def test_invalid_enum_value_raises_error(self):
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumRegistryStatus("invalid_status")

    def test_enum_in_operator(self):
        """Test that 'in' operator works with enum."""
        assert EnumRegistryStatus.HEALTHY in EnumRegistryStatus
        assert EnumRegistryStatus.MAINTENANCE in EnumRegistryStatus

    def test_enum_hash_consistency(self):
        """Test that enum members are hashable and consistent."""
        status_set = {EnumRegistryStatus.HEALTHY, EnumRegistryStatus.DEGRADED}
        assert len(status_set) == 2

        # Test that same enum members have same hash
        assert hash(EnumRegistryStatus.HEALTHY) == hash(EnumRegistryStatus.HEALTHY)

    def test_enum_repr(self):
        """Test that enum members have proper string representation."""
        assert (
            repr(EnumRegistryStatus.HEALTHY)
            == "<EnumRegistryStatus.HEALTHY: 'healthy'>"
        )
        assert (
            repr(EnumRegistryStatus.UNAVAILABLE)
            == "<EnumRegistryStatus.UNAVAILABLE: 'unavailable'>"
        )

    def test_enum_with_pydantic_compatibility(self):
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumRegistryStatus

        # Test valid values
        model = TestModel(status=EnumRegistryStatus.HEALTHY)
        assert model.status == EnumRegistryStatus.HEALTHY

        # Test string initialization
        model = TestModel(status="degraded")
        assert model.status == EnumRegistryStatus.DEGRADED

        # Test serialization
        data = model.model_dump()
        assert data["status"] == "degraded"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.status == EnumRegistryStatus.DEGRADED

    def test_registry_status_semantic_grouping(self):
        """Test semantic grouping of registry statuses."""
        # Operational statuses
        operational_statuses = {
            EnumRegistryStatus.HEALTHY,
            EnumRegistryStatus.DEGRADED,
            EnumRegistryStatus.UNAVAILABLE,
        }

        # Transitional statuses
        transitional_statuses = {
            EnumRegistryStatus.INITIALIZING,
            EnumRegistryStatus.MAINTENANCE,
        }

        all_statuses = operational_statuses | transitional_statuses
        actual_statuses = set(EnumRegistryStatus)

        assert all_statuses == actual_statuses, (
            "Registry status categorization is complete"
        )

    def test_status_severity_levels(self):
        """Test that registry statuses can be categorized by severity."""
        # Good status
        good_statuses = {EnumRegistryStatus.HEALTHY}

        # Warning statuses
        warning_statuses = {
            EnumRegistryStatus.DEGRADED,
            EnumRegistryStatus.INITIALIZING,
            EnumRegistryStatus.MAINTENANCE,
        }

        # Critical statuses
        critical_statuses = {EnumRegistryStatus.UNAVAILABLE}

        all_statuses = good_statuses | warning_statuses | critical_statuses
        actual_statuses = set(EnumRegistryStatus)

        assert all_statuses == actual_statuses, (
            "All registry statuses are categorized by severity"
        )

    def test_enum_case_sensitivity(self):
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            EnumRegistryStatus("HEALTHY")  # Should be "healthy"

        with pytest.raises(ValueError):
            EnumRegistryStatus("Healthy")  # Should be "healthy"

    def test_enum_serialization_json_compatible(self):
        """Test that enum values are JSON serializable."""
        import json

        for member in EnumRegistryStatus:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumRegistryStatus(deserialized)
            assert reconstructed == member


@pytest.mark.unit
class TestEnumRegistryStatusEdgeCases:
    """Test edge cases and error conditions for EnumRegistryStatus."""

    def test_enum_with_none_value(self):
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumRegistryStatus(None)

    def test_enum_with_empty_string(self):
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumRegistryStatus("")

    def test_enum_with_whitespace(self):
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumRegistryStatus(" healthy ")

    def test_enum_pickling(self):
        """Test that enum members can be pickled and unpickled."""
        import pickle

        for member in EnumRegistryStatus:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
