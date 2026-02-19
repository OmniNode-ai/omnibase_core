# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumFunctionLifecycleStatus.

Tests all aspects of the function lifecycle status enum including:
- Enum value validation
- Status classification methods (available, production_ready, testing_phase)
- Base status conversion (to_base_status, from_base_status)
- String representation
- JSON serialization compatibility
- Pydantic integration
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_base_status import EnumBaseStatus
from omnibase_core.enums.enum_function_lifecycle_status import (
    EnumFunctionLifecycleStatus,
    EnumFunctionStatus,
    EnumMetadataNodeStatus,
)


@pytest.mark.unit
class TestEnumFunctionLifecycleStatus:
    """Test cases for EnumFunctionLifecycleStatus."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "ACTIVE": "active",
            "INACTIVE": "inactive",
            "DEPRECATED": "deprecated",
            "DISABLED": "disabled",
            "EXPERIMENTAL": "experimental",
            "MAINTENANCE": "maintenance",
            "STABLE": "stable",
            "BETA": "beta",
            "ALPHA": "alpha",
        }

        for name, value in expected_values.items():
            status = getattr(EnumFunctionLifecycleStatus, name)
            assert status.value == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumFunctionLifecycleStatus.ACTIVE) == "active"
        assert str(EnumFunctionLifecycleStatus.DEPRECATED) == "deprecated"
        assert str(EnumFunctionLifecycleStatus.STABLE) == "stable"
        assert str(EnumFunctionLifecycleStatus.BETA) == "beta"

    def test_enum_count(self):
        """Test expected number of enum values."""
        assert len(EnumFunctionLifecycleStatus) == 9

    def test_is_available(self):
        """Test the is_available class method."""
        # Available statuses
        available_statuses = [
            EnumFunctionLifecycleStatus.ACTIVE,
            EnumFunctionLifecycleStatus.EXPERIMENTAL,
            EnumFunctionLifecycleStatus.STABLE,
            EnumFunctionLifecycleStatus.BETA,
            EnumFunctionLifecycleStatus.ALPHA,
        ]

        for status in available_statuses:
            assert EnumFunctionLifecycleStatus.is_available(status) is True

        # Unavailable statuses
        unavailable_statuses = [
            EnumFunctionLifecycleStatus.INACTIVE,
            EnumFunctionLifecycleStatus.DEPRECATED,
            EnumFunctionLifecycleStatus.DISABLED,
            EnumFunctionLifecycleStatus.MAINTENANCE,
        ]

        for status in unavailable_statuses:
            assert EnumFunctionLifecycleStatus.is_available(status) is False

    def test_requires_warning(self):
        """Test the requires_warning class method."""
        # Statuses requiring warning
        warning_statuses = [
            EnumFunctionLifecycleStatus.DEPRECATED,
            EnumFunctionLifecycleStatus.EXPERIMENTAL,
            EnumFunctionLifecycleStatus.MAINTENANCE,
            EnumFunctionLifecycleStatus.BETA,
            EnumFunctionLifecycleStatus.ALPHA,
        ]

        for status in warning_statuses:
            assert EnumFunctionLifecycleStatus.requires_warning(status) is True

        # Statuses not requiring warning
        no_warning_statuses = [
            EnumFunctionLifecycleStatus.ACTIVE,
            EnumFunctionLifecycleStatus.INACTIVE,
            EnumFunctionLifecycleStatus.DISABLED,
            EnumFunctionLifecycleStatus.STABLE,
        ]

        for status in no_warning_statuses:
            assert EnumFunctionLifecycleStatus.requires_warning(status) is False

    def test_is_production_ready(self):
        """Test the is_production_ready class method."""
        # Production-ready statuses
        assert (
            EnumFunctionLifecycleStatus.is_production_ready(
                EnumFunctionLifecycleStatus.ACTIVE
            )
            is True
        )
        assert (
            EnumFunctionLifecycleStatus.is_production_ready(
                EnumFunctionLifecycleStatus.STABLE
            )
            is True
        )

        # Non-production-ready statuses
        non_prod_statuses = [
            EnumFunctionLifecycleStatus.INACTIVE,
            EnumFunctionLifecycleStatus.DEPRECATED,
            EnumFunctionLifecycleStatus.DISABLED,
            EnumFunctionLifecycleStatus.EXPERIMENTAL,
            EnumFunctionLifecycleStatus.MAINTENANCE,
            EnumFunctionLifecycleStatus.BETA,
            EnumFunctionLifecycleStatus.ALPHA,
        ]

        for status in non_prod_statuses:
            assert EnumFunctionLifecycleStatus.is_production_ready(status) is False

    def test_is_testing_phase(self):
        """Test the is_testing_phase class method."""
        # Testing phase statuses
        testing_statuses = [
            EnumFunctionLifecycleStatus.EXPERIMENTAL,
            EnumFunctionLifecycleStatus.BETA,
            EnumFunctionLifecycleStatus.ALPHA,
        ]

        for status in testing_statuses:
            assert EnumFunctionLifecycleStatus.is_testing_phase(status) is True

        # Non-testing phase statuses
        non_testing_statuses = [
            EnumFunctionLifecycleStatus.ACTIVE,
            EnumFunctionLifecycleStatus.INACTIVE,
            EnumFunctionLifecycleStatus.DEPRECATED,
            EnumFunctionLifecycleStatus.DISABLED,
            EnumFunctionLifecycleStatus.MAINTENANCE,
            EnumFunctionLifecycleStatus.STABLE,
        ]

        for status in non_testing_statuses:
            assert EnumFunctionLifecycleStatus.is_testing_phase(status) is False

    def test_is_stable_release(self):
        """Test the is_stable_release class method."""
        # Stable release statuses
        assert (
            EnumFunctionLifecycleStatus.is_stable_release(
                EnumFunctionLifecycleStatus.ACTIVE
            )
            is True
        )
        assert (
            EnumFunctionLifecycleStatus.is_stable_release(
                EnumFunctionLifecycleStatus.STABLE
            )
            is True
        )

        # Non-stable release statuses
        for status in EnumFunctionLifecycleStatus:
            if status not in {
                EnumFunctionLifecycleStatus.ACTIVE,
                EnumFunctionLifecycleStatus.STABLE,
            }:
                assert EnumFunctionLifecycleStatus.is_stable_release(status) is False

    def test_requires_migration_planning(self):
        """Test the requires_migration_planning class method."""
        # Only DEPRECATED requires migration planning
        assert (
            EnumFunctionLifecycleStatus.requires_migration_planning(
                EnumFunctionLifecycleStatus.DEPRECATED
            )
            is True
        )

        # All other statuses don't require migration planning
        for status in EnumFunctionLifecycleStatus:
            if status != EnumFunctionLifecycleStatus.DEPRECATED:
                assert (
                    EnumFunctionLifecycleStatus.requires_migration_planning(status)
                    is False
                )

    def test_is_temporarily_unavailable(self):
        """Test the is_temporarily_unavailable class method."""
        # Temporarily unavailable statuses
        temp_unavailable = [
            EnumFunctionLifecycleStatus.DISABLED,
            EnumFunctionLifecycleStatus.MAINTENANCE,
        ]

        for status in temp_unavailable:
            assert (
                EnumFunctionLifecycleStatus.is_temporarily_unavailable(status) is True
            )

        # Not temporarily unavailable
        for status in EnumFunctionLifecycleStatus:
            if status not in temp_unavailable:
                assert (
                    EnumFunctionLifecycleStatus.is_temporarily_unavailable(status)
                    is False
                )

    def test_get_stability_order(self):
        """Test the get_stability_order class method."""
        # Test specific stability order values
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.STABLE
            )
            == 5
        )
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.ACTIVE
            )
            == 4
        )
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.EXPERIMENTAL
            )
            == 3
        )
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.BETA
            )
            == 2
        )
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.ALPHA
            )
            == 1
        )
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.DISABLED
            )
            == 0
        )
        assert (
            EnumFunctionLifecycleStatus.get_stability_order(
                EnumFunctionLifecycleStatus.INACTIVE
            )
            == 0
        )

        # Test ordering relationship
        assert EnumFunctionLifecycleStatus.get_stability_order(
            EnumFunctionLifecycleStatus.STABLE
        ) > EnumFunctionLifecycleStatus.get_stability_order(
            EnumFunctionLifecycleStatus.BETA
        )
        assert EnumFunctionLifecycleStatus.get_stability_order(
            EnumFunctionLifecycleStatus.BETA
        ) > EnumFunctionLifecycleStatus.get_stability_order(
            EnumFunctionLifecycleStatus.ALPHA
        )

    def test_to_base_status(self):
        """Test to_base_status conversion method."""
        # Direct base status mappings
        assert (
            EnumFunctionLifecycleStatus.ACTIVE.to_base_status() == EnumBaseStatus.ACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.INACTIVE.to_base_status()
            == EnumBaseStatus.INACTIVE
        )

        # Lifecycle-specific mappings
        assert (
            EnumFunctionLifecycleStatus.DEPRECATED.to_base_status()
            == EnumBaseStatus.ACTIVE
        )  # Still active but deprecated
        assert (
            EnumFunctionLifecycleStatus.DISABLED.to_base_status()
            == EnumBaseStatus.INACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.EXPERIMENTAL.to_base_status()
            == EnumBaseStatus.ACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.MAINTENANCE.to_base_status()
            == EnumBaseStatus.INACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.STABLE.to_base_status() == EnumBaseStatus.ACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.BETA.to_base_status() == EnumBaseStatus.ACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.ALPHA.to_base_status() == EnumBaseStatus.ACTIVE
        )

    def test_from_base_status(self):
        """Test from_base_status class method."""
        # Test valid conversions (direct mappings only)
        assert (
            EnumFunctionLifecycleStatus.from_base_status(EnumBaseStatus.ACTIVE)
            == EnumFunctionLifecycleStatus.ACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.from_base_status(EnumBaseStatus.INACTIVE)
            == EnumFunctionLifecycleStatus.INACTIVE
        )

    def test_from_base_status_invalid(self):
        """Test from_base_status raises ValueError for unmapped values."""
        # Base statuses without direct lifecycle equivalents should raise ValueError
        unmapped_statuses = [
            EnumBaseStatus.PENDING,
            EnumBaseStatus.RUNNING,
            EnumBaseStatus.COMPLETED,
            EnumBaseStatus.FAILED,
            EnumBaseStatus.VALID,
            EnumBaseStatus.INVALID,
            EnumBaseStatus.UNKNOWN,
        ]

        for base_status in unmapped_statuses:
            with pytest.raises(ValueError):
                EnumFunctionLifecycleStatus.from_base_status(base_status)

    def test_base_status_roundtrip(self):
        """Test roundtrip conversion base -> lifecycle -> base for direct mappings."""
        # Only ACTIVE and INACTIVE can roundtrip successfully
        roundtrip_statuses = [
            EnumBaseStatus.ACTIVE,
            EnumBaseStatus.INACTIVE,
        ]

        for base_status in roundtrip_statuses:
            lifecycle_status = EnumFunctionLifecycleStatus.from_base_status(base_status)
            back_to_base = lifecycle_status.to_base_status()
            assert back_to_base == base_status, (
                f"Roundtrip failed for {base_status}: "
                f"got {back_to_base} via {lifecycle_status}"
            )

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumFunctionLifecycleStatus.ACTIVE == EnumFunctionLifecycleStatus.ACTIVE
        assert EnumFunctionLifecycleStatus.STABLE != EnumFunctionLifecycleStatus.BETA

    def test_enum_membership(self):
        """Test enum membership checking."""
        for status in EnumFunctionLifecycleStatus:
            assert status in EnumFunctionLifecycleStatus

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        status = EnumFunctionLifecycleStatus.STABLE
        json_str = json.dumps(status, default=str)
        assert json_str == '"stable"'

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class LifecycleModel(BaseModel):
            status: EnumFunctionLifecycleStatus

        # Test valid enum assignment
        model = LifecycleModel(status=EnumFunctionLifecycleStatus.STABLE)
        assert model.status == EnumFunctionLifecycleStatus.STABLE

        # Test string assignment
        model = LifecycleModel(status="beta")
        assert model.status == EnumFunctionLifecycleStatus.BETA

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            LifecycleModel(status="invalid_status")

    def test_compatibility_aliases(self):
        """Test that compatibility aliases work correctly."""
        # EnumFunctionStatus alias
        assert EnumFunctionStatus is EnumFunctionLifecycleStatus
        assert EnumFunctionStatus.ACTIVE == EnumFunctionLifecycleStatus.ACTIVE

        # EnumMetadataNodeStatus alias
        assert EnumMetadataNodeStatus is EnumFunctionLifecycleStatus
        assert EnumMetadataNodeStatus.STABLE == EnumFunctionLifecycleStatus.STABLE

    def test_all_statuses_have_stability_order(self):
        """Test that all statuses have a defined stability order."""
        for status in EnumFunctionLifecycleStatus:
            order = EnumFunctionLifecycleStatus.get_stability_order(status)
            assert isinstance(order, int)
            assert order >= 0

    def test_lifecycle_consistency(self):
        """Test logical consistency of lifecycle categorization."""
        for status in EnumFunctionLifecycleStatus:
            # If production ready, should be available
            if EnumFunctionLifecycleStatus.is_production_ready(status):
                assert EnumFunctionLifecycleStatus.is_available(status)

            # If testing phase, should be available but not production ready
            if EnumFunctionLifecycleStatus.is_testing_phase(status):
                assert EnumFunctionLifecycleStatus.is_available(status)
                assert not EnumFunctionLifecycleStatus.is_production_ready(status)

            # If temporarily unavailable, should not be available
            if EnumFunctionLifecycleStatus.is_temporarily_unavailable(status):
                assert not EnumFunctionLifecycleStatus.is_available(status)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
