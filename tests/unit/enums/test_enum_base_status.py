from enum import Enum

import pytest

from omnibase_core.enums.enum_base_status import EnumBaseStatus


@pytest.mark.unit
class TestEnumBaseStatus:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        # Core lifecycle states
        assert EnumBaseStatus.INACTIVE == "inactive"
        assert EnumBaseStatus.ACTIVE == "active"
        assert EnumBaseStatus.PENDING == "pending"

        # Core execution states
        assert EnumBaseStatus.RUNNING == "running"
        assert EnumBaseStatus.COMPLETED == "completed"
        assert EnumBaseStatus.FAILED == "failed"

        # Core quality states
        assert EnumBaseStatus.VALID == "valid"
        assert EnumBaseStatus.INVALID == "invalid"
        assert EnumBaseStatus.UNKNOWN == "unknown"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumBaseStatus, str)
        assert issubclass(EnumBaseStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumBaseStatus.ACTIVE
        assert isinstance(status, str)
        assert status == "active"
        assert len(status) == 6
        assert status.startswith("act")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumBaseStatus)
        assert len(values) == 9
        assert EnumBaseStatus.ACTIVE in values
        assert EnumBaseStatus.UNKNOWN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumBaseStatus.RUNNING in EnumBaseStatus
        assert "running" in [e.value for e in EnumBaseStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumBaseStatus.COMPLETED
        status2 = EnumBaseStatus.COMPLETED
        status3 = EnumBaseStatus.FAILED

        assert status1 == status2
        assert status1 != status3
        assert status1 == "completed"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumBaseStatus.VALID
        serialized = status.value
        assert serialized == "valid"
        import json

        json_str = json.dumps(status)
        assert json_str == '"valid"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumBaseStatus("pending")
        assert status == EnumBaseStatus.PENDING

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumBaseStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "inactive",
            "active",
            "pending",
            "running",
            "completed",
            "failed",
            "valid",
            "invalid",
            "unknown",
        }
        actual_values = {e.value for e in EnumBaseStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumBaseStatus.__doc__ is not None
        assert "base status enumeration" in EnumBaseStatus.__doc__.lower()

    def test_is_active_state_method(self):
        """Test is_active_state method."""
        # Active states
        assert EnumBaseStatus.ACTIVE.is_active_state()
        assert EnumBaseStatus.RUNNING.is_active_state()
        assert EnumBaseStatus.PENDING.is_active_state()

        # Non-active states
        assert not EnumBaseStatus.INACTIVE.is_active_state()
        assert not EnumBaseStatus.COMPLETED.is_active_state()
        assert not EnumBaseStatus.FAILED.is_active_state()

    def test_is_terminal_state_method(self):
        """Test is_terminal_state method."""
        # Terminal states
        assert EnumBaseStatus.COMPLETED.is_terminal_state()
        assert EnumBaseStatus.FAILED.is_terminal_state()
        assert EnumBaseStatus.INACTIVE.is_terminal_state()

        # Non-terminal states
        assert not EnumBaseStatus.ACTIVE.is_terminal_state()
        assert not EnumBaseStatus.RUNNING.is_terminal_state()
        assert not EnumBaseStatus.PENDING.is_terminal_state()

    def test_is_error_state_method(self):
        """Test is_error_state method."""
        # Error states
        assert EnumBaseStatus.FAILED.is_error_state()
        assert EnumBaseStatus.INVALID.is_error_state()

        # Non-error states
        assert not EnumBaseStatus.ACTIVE.is_error_state()
        assert not EnumBaseStatus.COMPLETED.is_error_state()
        assert not EnumBaseStatus.VALID.is_error_state()

    def test_is_pending_state_method(self):
        """Test is_pending_state method."""
        # Pending states
        assert EnumBaseStatus.PENDING.is_pending_state()
        assert EnumBaseStatus.RUNNING.is_pending_state()
        assert EnumBaseStatus.UNKNOWN.is_pending_state()

        # Non-pending states
        assert not EnumBaseStatus.ACTIVE.is_pending_state()
        assert not EnumBaseStatus.COMPLETED.is_pending_state()
        assert not EnumBaseStatus.FAILED.is_pending_state()

    def test_is_quality_state_method(self):
        """Test is_quality_state method."""
        # Quality states
        assert EnumBaseStatus.VALID.is_quality_state()
        assert EnumBaseStatus.INVALID.is_quality_state()
        assert EnumBaseStatus.UNKNOWN.is_quality_state()

        # Non-quality states
        assert not EnumBaseStatus.ACTIVE.is_quality_state()
        assert not EnumBaseStatus.RUNNING.is_quality_state()
        assert not EnumBaseStatus.COMPLETED.is_quality_state()

    def test_status_categorization_completeness(self):
        """Test that all statuses are categorized by at least one method."""
        all_statuses = set(EnumBaseStatus)

        # Get statuses categorized by each method
        active_statuses = {e for e in EnumBaseStatus if e.is_active_state()}
        terminal_statuses = {e for e in EnumBaseStatus if e.is_terminal_state()}
        error_statuses = {e for e in EnumBaseStatus if e.is_error_state()}
        pending_statuses = {e for e in EnumBaseStatus if e.is_pending_state()}
        quality_statuses = {e for e in EnumBaseStatus if e.is_quality_state()}

        # All statuses should be categorized by at least one method
        categorized_statuses = (
            active_statuses
            | terminal_statuses
            | error_statuses
            | pending_statuses
            | quality_statuses
        )
        assert len(categorized_statuses) == len(
            all_statuses
        )  # All statuses should be categorized

    def test_status_logical_groupings(self):
        """Test logical groupings of status values."""
        # Lifecycle states
        lifecycle_states = {
            EnumBaseStatus.INACTIVE,
            EnumBaseStatus.ACTIVE,
            EnumBaseStatus.PENDING,
        }

        # Execution states
        execution_states = {
            EnumBaseStatus.RUNNING,
            EnumBaseStatus.COMPLETED,
            EnumBaseStatus.FAILED,
        }

        # Quality states
        quality_states = {
            EnumBaseStatus.VALID,
            EnumBaseStatus.INVALID,
            EnumBaseStatus.UNKNOWN,
        }

        # Test that all states are covered
        all_grouped_states = lifecycle_states | execution_states | quality_states
        assert all_grouped_states == set(EnumBaseStatus)

    def test_status_workflow_progression(self):
        """Test logical workflow progression of statuses."""
        # Typical workflow: pending -> active -> completed
        workflow_states = [
            EnumBaseStatus.PENDING,
            EnumBaseStatus.ACTIVE,
            EnumBaseStatus.COMPLETED,
        ]

        # All workflow states should be valid
        for state in workflow_states:
            assert state in EnumBaseStatus

    def test_status_state_transitions(self):
        """Test logical state transitions."""
        # Active to terminal transitions
        assert EnumBaseStatus.ACTIVE.is_active_state()
        assert not EnumBaseStatus.ACTIVE.is_terminal_state()

        assert not EnumBaseStatus.COMPLETED.is_active_state()
        assert EnumBaseStatus.COMPLETED.is_terminal_state()

        # Error state transitions
        assert EnumBaseStatus.FAILED.is_error_state()
        assert EnumBaseStatus.FAILED.is_terminal_state()

        # Pending state transitions
        assert EnumBaseStatus.PENDING.is_pending_state()
        assert EnumBaseStatus.PENDING.is_active_state()  # Pending is considered active

    def test_base_status_universality(self):
        """Test that base status values are truly universal."""
        # All values should be fundamental and not domain-specific
        universal_values = {
            "inactive",
            "active",
            "pending",
            "running",
            "completed",
            "failed",
            "valid",
            "invalid",
            "unknown",
        }
        actual_values = {e.value for e in EnumBaseStatus}
        assert actual_values == universal_values

        # Values should be simple and not contain domain-specific terms
        for value in actual_values:
            assert len(value) <= 10  # Should be concise
            assert value.islower()  # Should be lowercase
            assert "_" not in value or value.count("_") <= 1  # Should be simple

    def test_base_status_extensibility(self):
        """Test that base status can be extended by domain-specific enums."""
        # Base status should provide fundamental building blocks
        fundamental_categories = {
            "lifecycle": {
                EnumBaseStatus.INACTIVE,
                EnumBaseStatus.ACTIVE,
                EnumBaseStatus.PENDING,
            },
            "execution": {
                EnumBaseStatus.RUNNING,
                EnumBaseStatus.COMPLETED,
                EnumBaseStatus.FAILED,
            },
            "quality": {
                EnumBaseStatus.VALID,
                EnumBaseStatus.INVALID,
                EnumBaseStatus.UNKNOWN,
            },
        }

        # Each category should be complete and non-overlapping
        all_categories = set()
        for category_states in fundamental_categories.values():
            all_categories.update(category_states)

        assert all_categories == set(EnumBaseStatus)

        # Categories should not overlap
        lifecycle = fundamental_categories["lifecycle"]
        execution = fundamental_categories["execution"]
        quality = fundamental_categories["quality"]

        assert lifecycle.isdisjoint(execution)
        assert lifecycle.isdisjoint(quality)
        assert execution.isdisjoint(quality)
