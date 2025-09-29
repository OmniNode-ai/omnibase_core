"""
Unit tests for EnumStatus.

Tests all aspects of the status enum including:
- Enum value validation
- Helper methods for state categorization
- String representation
- JSON serialization compatibility
- Pydantic integration
- State transition logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_status import EnumStatus


class TestEnumStatus:
    """Test cases for EnumStatus."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            # Basic status states
            "ACTIVE": "active",
            "INACTIVE": "inactive",
            "PENDING": "pending",
            # Processing states
            "PROCESSING": "processing",
            "COMPLETED": "completed",
            "FAILED": "failed",
            # Lifecycle states
            "CREATED": "created",
            "UPDATED": "updated",
            "DELETED": "deleted",
            "ARCHIVED": "archived",
            # Validation states
            "VALID": "valid",
            "INVALID": "invalid",
            "UNKNOWN": "unknown",
            # Approval states
            "APPROVED": "approved",
            "REJECTED": "rejected",
            "UNDER_REVIEW": "under_review",
            # Availability states
            "AVAILABLE": "available",
            "UNAVAILABLE": "unavailable",
            "MAINTENANCE": "maintenance",
            # Quality states
            "DRAFT": "draft",
            "PUBLISHED": "published",
            "DEPRECATED": "deprecated",
            # Operational states
            "ENABLED": "enabled",
            "DISABLED": "disabled",
            "SUSPENDED": "suspended",
        }

        for name, value in expected_values.items():
            status = getattr(EnumStatus, name)
            assert status.value == value
            # Test that the enum value is correct, not requiring specific str() behavior

    def test_string_representation(self):
        """Test string representation of enum values."""
        # Test that enum values can be used as strings and have correct values
        assert EnumStatus.ACTIVE.value == "active"
        assert EnumStatus.PROCESSING.value == "processing"
        assert EnumStatus.COMPLETED.value == "completed"
        assert EnumStatus.FAILED.value == "failed"

        # Test string equality (since it inherits from str)
        assert EnumStatus.ACTIVE == "active"
        assert EnumStatus.PROCESSING == "processing"

    def test_is_active_state(self):
        """Test the is_active_state helper method."""
        # Active states
        active_states = [
            EnumStatus.ACTIVE,
            EnumStatus.PROCESSING,
            EnumStatus.ENABLED,
            EnumStatus.AVAILABLE,
            EnumStatus.PUBLISHED,
        ]

        for status in active_states:
            assert status.is_active_state() is True

        # Non-active states
        non_active_states = [
            EnumStatus.INACTIVE,
            EnumStatus.PENDING,
            EnumStatus.COMPLETED,
            EnumStatus.FAILED,
            EnumStatus.DELETED,
            EnumStatus.DISABLED,
            EnumStatus.SUSPENDED,
            EnumStatus.DRAFT,
        ]

        for status in non_active_states:
            assert status.is_active_state() is False

    def test_is_terminal_state(self):
        """Test the is_terminal_state helper method."""
        # Terminal states
        terminal_states = [
            EnumStatus.COMPLETED,
            EnumStatus.FAILED,
            EnumStatus.DELETED,
            EnumStatus.ARCHIVED,
            EnumStatus.DEPRECATED,
        ]

        for status in terminal_states:
            assert status.is_terminal_state() is True

        # Non-terminal states
        non_terminal_states = [
            EnumStatus.ACTIVE,
            EnumStatus.INACTIVE,
            EnumStatus.PENDING,
            EnumStatus.PROCESSING,
            EnumStatus.CREATED,
            EnumStatus.UPDATED,
            EnumStatus.ENABLED,
            EnumStatus.DISABLED,
            EnumStatus.DRAFT,
            EnumStatus.PUBLISHED,
        ]

        for status in non_terminal_states:
            assert status.is_terminal_state() is False

    def test_is_error_state(self):
        """Test the is_error_state helper method."""
        # Error states
        error_states = [
            EnumStatus.FAILED,
            EnumStatus.INVALID,
            EnumStatus.REJECTED,
            EnumStatus.UNAVAILABLE,
        ]

        for status in error_states:
            assert status.is_error_state() is True

        # Non-error states
        non_error_states = [
            EnumStatus.ACTIVE,
            EnumStatus.COMPLETED,
            EnumStatus.PENDING,
            EnumStatus.PROCESSING,
            EnumStatus.APPROVED,
            EnumStatus.AVAILABLE,
            EnumStatus.VALID,
            EnumStatus.ENABLED,
        ]

        for status in non_error_states:
            assert status.is_error_state() is False

    def test_is_pending_state(self):
        """Test the is_pending_state helper method."""
        # Pending states
        pending_states = [
            EnumStatus.PENDING,
            EnumStatus.PROCESSING,
            EnumStatus.UNDER_REVIEW,
            EnumStatus.DRAFT,
        ]

        for status in pending_states:
            assert status.is_pending_state() is True

        # Non-pending states
        non_pending_states = [
            EnumStatus.ACTIVE,
            EnumStatus.COMPLETED,
            EnumStatus.FAILED,
            EnumStatus.APPROVED,
            EnumStatus.REJECTED,
            EnumStatus.PUBLISHED,
            EnumStatus.ENABLED,
            EnumStatus.DISABLED,
        ]

        for status in non_pending_states:
            assert status.is_pending_state() is False

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumStatus.ACTIVE == EnumStatus.ACTIVE
        assert EnumStatus.COMPLETED != EnumStatus.FAILED
        assert EnumStatus.PENDING == EnumStatus.PENDING

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_statuses = list(EnumStatus)
        for status in all_statuses:
            assert status in EnumStatus

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        statuses = list(EnumStatus)

        # Count the actual number of values from the enum definition
        expected_values = {
            "active",
            "inactive",
            "pending",
            "processing",
            "completed",
            "failed",
            "created",
            "updated",
            "deleted",
            "archived",
            "valid",
            "invalid",
            "unknown",
            "approved",
            "rejected",
            "under_review",
            "available",
            "unavailable",
            "maintenance",
            "draft",
            "published",
            "deprecated",
            "enabled",
            "disabled",
            "suspended",
        }

        assert len(statuses) == len(expected_values)  # Should match expected count

        status_values = {status.value for status in statuses}
        assert status_values == expected_values

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        status = EnumStatus.PROCESSING
        json_str = json.dumps(status, default=str)
        assert json_str == '"processing"'

        # Test in dictionary
        data = {"status": EnumStatus.COMPLETED}
        json_str = json.dumps(data, default=str)
        assert '"status": "completed"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EnumStatusModel(BaseModel):
            status: EnumStatus

        # Test valid enum assignment
        model = EnumStatusModel(status=EnumStatus.ACTIVE)
        assert model.status == EnumStatus.ACTIVE

        # Test string assignment (should work due to str inheritance)
        model = EnumStatusModel(status="completed")
        assert model.status == EnumStatus.COMPLETED

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EnumStatusModel(status="invalid_status")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class StatusModel(BaseModel):
            status: EnumStatus

        model = StatusModel(status=EnumStatus.PUBLISHED)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"status": "published"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"status":"published"}'

    def test_state_categorization_logic(self):
        """Test comprehensive state categorization logic."""
        # Test that no status is in multiple exclusive categories where it shouldn't be

        # Error states should generally not be active states
        error_states = [s for s in EnumStatus if s.is_error_state()]
        active_states = [s for s in EnumStatus if s.is_active_state()]

        error_and_active = set(error_states).intersection(set(active_states))
        assert (
            len(error_and_active) == 0
        ), f"Error states should not be active: {error_and_active}"

        # Terminal states should not be pending states
        terminal_states = [s for s in EnumStatus if s.is_terminal_state()]
        pending_states = [s for s in EnumStatus if s.is_pending_state()]

        terminal_and_pending = set(terminal_states).intersection(set(pending_states))
        assert (
            len(terminal_and_pending) == 0
        ), f"Terminal states should not be pending: {terminal_and_pending}"

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity
        assert EnumStatus.ACTIVE.value == "active"
        assert EnumStatus.ACTIVE.value != "ACTIVE"
        assert EnumStatus.ACTIVE.value != "Active"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumStatus("invalid_status")

    def test_comprehensive_state_transitions(self):
        """Test logical state transition scenarios."""
        # Test common workflow states
        workflow_states = [
            EnumStatus.CREATED,
            EnumStatus.PENDING,
            EnumStatus.PROCESSING,
            EnumStatus.COMPLETED,
        ]

        # Verify workflow progression makes sense
        assert EnumStatus.CREATED.is_pending_state() is False
        assert EnumStatus.PENDING.is_pending_state() is True
        assert EnumStatus.PROCESSING.is_pending_state() is True
        assert EnumStatus.PROCESSING.is_active_state() is True
        assert EnumStatus.COMPLETED.is_terminal_state() is True

        # Test approval workflow
        approval_states = [
            EnumStatus.DRAFT,
            EnumStatus.UNDER_REVIEW,
            EnumStatus.APPROVED,
            EnumStatus.PUBLISHED,
        ]

        assert EnumStatus.DRAFT.is_pending_state() is True
        assert EnumStatus.UNDER_REVIEW.is_pending_state() is True
        assert EnumStatus.APPROVED.is_pending_state() is False
        assert EnumStatus.PUBLISHED.is_active_state() is True

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values can be serialized via their value property
        data = {"status": EnumStatus.MAINTENANCE.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "status: maintenance" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["status"] == "maintenance"

        # Test that the enum value equals the string
        assert EnumStatus.MAINTENANCE == "maintenance"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
