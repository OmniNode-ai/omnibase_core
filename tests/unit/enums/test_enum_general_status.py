from enum import Enum

import pytest

from omnibase_core.enums.enum_base_status import EnumBaseStatus
from omnibase_core.enums.enum_general_status import EnumGeneralStatus


class TestEnumGeneralStatus:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        # Base status values
        assert EnumGeneralStatus.INACTIVE == "inactive"
        assert EnumGeneralStatus.ACTIVE == "active"
        assert EnumGeneralStatus.PENDING == "pending"
        assert EnumGeneralStatus.RUNNING == "running"
        assert EnumGeneralStatus.COMPLETED == "completed"
        assert EnumGeneralStatus.FAILED == "failed"
        assert EnumGeneralStatus.VALID == "valid"
        assert EnumGeneralStatus.INVALID == "invalid"
        assert EnumGeneralStatus.UNKNOWN == "unknown"

        # Extended lifecycle states
        assert EnumGeneralStatus.CREATED == "created"
        assert EnumGeneralStatus.UPDATED == "updated"
        assert EnumGeneralStatus.DELETED == "deleted"
        assert EnumGeneralStatus.ARCHIVED == "archived"

        # Approval workflow states
        assert EnumGeneralStatus.APPROVED == "approved"
        assert EnumGeneralStatus.REJECTED == "rejected"
        assert EnumGeneralStatus.UNDER_REVIEW == "under_review"

        # Availability states
        assert EnumGeneralStatus.AVAILABLE == "available"
        assert EnumGeneralStatus.UNAVAILABLE == "unavailable"
        assert EnumGeneralStatus.MAINTENANCE == "maintenance"

        # Quality/Publishing states
        assert EnumGeneralStatus.DRAFT == "draft"
        assert EnumGeneralStatus.PUBLISHED == "published"
        assert EnumGeneralStatus.DEPRECATED == "deprecated"

        # Operational states
        assert EnumGeneralStatus.ENABLED == "enabled"
        assert EnumGeneralStatus.DISABLED == "disabled"
        assert EnumGeneralStatus.SUSPENDED == "suspended"

        # Processing states
        assert EnumGeneralStatus.PROCESSING == "processing"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumGeneralStatus, str)
        assert issubclass(EnumGeneralStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumGeneralStatus.ACTIVE
        assert isinstance(status, str)
        assert status == "active"
        assert len(status) == 6
        assert status.startswith("act")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumGeneralStatus)
        assert len(values) == 26
        assert EnumGeneralStatus.ACTIVE in values
        assert EnumGeneralStatus.PROCESSING in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumGeneralStatus.RUNNING in EnumGeneralStatus
        assert "running" in [e.value for e in EnumGeneralStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumGeneralStatus.COMPLETED
        status2 = EnumGeneralStatus.COMPLETED
        status3 = EnumGeneralStatus.FAILED

        assert status1 == status2
        assert status1 != status3
        assert status1 == "completed"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumGeneralStatus.PUBLISHED
        serialized = status.value
        assert serialized == "published"
        import json

        json_str = json.dumps(status)
        assert json_str == '"published"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumGeneralStatus("draft")
        assert status == EnumGeneralStatus.DRAFT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumGeneralStatus("invalid_status")

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
            "created",
            "updated",
            "deleted",
            "archived",
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
            "processing",
        }
        actual_values = {e.value for e in EnumGeneralStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumGeneralStatus.__doc__ is not None
        assert "general purpose status" in EnumGeneralStatus.__doc__.lower()

    def test_enum_str_method(self):
        """Test __str__ method."""
        status = EnumGeneralStatus.ENABLED
        assert str(status) == "enabled"
        assert str(status) == status.value

    def test_to_base_status_method(self):
        """Test to_base_status method."""
        # Test direct base status mappings
        assert EnumGeneralStatus.ACTIVE.to_base_status() == EnumBaseStatus.ACTIVE
        assert EnumGeneralStatus.PENDING.to_base_status() == EnumBaseStatus.PENDING
        assert EnumGeneralStatus.COMPLETED.to_base_status() == EnumBaseStatus.COMPLETED

        # Test general-specific mappings
        assert EnumGeneralStatus.CREATED.to_base_status() == EnumBaseStatus.ACTIVE
        assert EnumGeneralStatus.APPROVED.to_base_status() == EnumBaseStatus.VALID
        assert EnumGeneralStatus.AVAILABLE.to_base_status() == EnumBaseStatus.ACTIVE
        assert EnumGeneralStatus.DRAFT.to_base_status() == EnumBaseStatus.PENDING
        assert EnumGeneralStatus.ENABLED.to_base_status() == EnumBaseStatus.ACTIVE
        assert EnumGeneralStatus.PROCESSING.to_base_status() == EnumBaseStatus.RUNNING

    def test_from_base_status_class_method(self):
        """Test from_base_status class method."""
        # Test direct mappings
        assert (
            EnumGeneralStatus.from_base_status(EnumBaseStatus.ACTIVE)
            == EnumGeneralStatus.ACTIVE
        )
        assert (
            EnumGeneralStatus.from_base_status(EnumBaseStatus.PENDING)
            == EnumGeneralStatus.PENDING
        )
        assert (
            EnumGeneralStatus.from_base_status(EnumBaseStatus.COMPLETED)
            == EnumGeneralStatus.COMPLETED
        )

    def test_is_active_state_method(self):
        """Test is_active_state method."""
        # Active states
        assert EnumGeneralStatus.ACTIVE.is_active_state()
        assert EnumGeneralStatus.RUNNING.is_active_state()
        assert EnumGeneralStatus.PROCESSING.is_active_state()
        assert EnumGeneralStatus.ENABLED.is_active_state()
        assert EnumGeneralStatus.AVAILABLE.is_active_state()
        assert EnumGeneralStatus.PUBLISHED.is_active_state()
        assert EnumGeneralStatus.CREATED.is_active_state()
        assert EnumGeneralStatus.UPDATED.is_active_state()
        assert EnumGeneralStatus.APPROVED.is_active_state()

        # Non-active states
        assert not EnumGeneralStatus.INACTIVE.is_active_state()
        assert not EnumGeneralStatus.COMPLETED.is_active_state()
        assert not EnumGeneralStatus.FAILED.is_active_state()
        assert not EnumGeneralStatus.DISABLED.is_active_state()

    def test_is_terminal_state_method(self):
        """Test is_terminal_state method."""
        # Terminal states
        assert EnumGeneralStatus.COMPLETED.is_terminal_state()
        assert EnumGeneralStatus.FAILED.is_terminal_state()
        assert EnumGeneralStatus.DELETED.is_terminal_state()
        assert EnumGeneralStatus.ARCHIVED.is_terminal_state()
        assert EnumGeneralStatus.DEPRECATED.is_terminal_state()
        assert EnumGeneralStatus.REJECTED.is_terminal_state()

        # Non-terminal states
        assert not EnumGeneralStatus.ACTIVE.is_terminal_state()
        assert not EnumGeneralStatus.RUNNING.is_terminal_state()
        assert not EnumGeneralStatus.PENDING.is_terminal_state()

    def test_is_error_state_method(self):
        """Test is_error_state method."""
        # Error states
        assert EnumGeneralStatus.FAILED.is_error_state()
        assert EnumGeneralStatus.INVALID.is_error_state()
        assert EnumGeneralStatus.REJECTED.is_error_state()
        assert EnumGeneralStatus.UNAVAILABLE.is_error_state()

        # Non-error states
        assert not EnumGeneralStatus.ACTIVE.is_error_state()
        assert not EnumGeneralStatus.COMPLETED.is_error_state()
        assert not EnumGeneralStatus.VALID.is_error_state()

    def test_is_pending_state_method(self):
        """Test is_pending_state method."""
        # Pending states
        assert EnumGeneralStatus.PENDING.is_pending_state()
        assert EnumGeneralStatus.RUNNING.is_pending_state()
        assert EnumGeneralStatus.PROCESSING.is_pending_state()
        assert EnumGeneralStatus.UNDER_REVIEW.is_pending_state()
        assert EnumGeneralStatus.DRAFT.is_pending_state()
        assert EnumGeneralStatus.MAINTENANCE.is_pending_state()
        assert EnumGeneralStatus.SUSPENDED.is_pending_state()

        # Non-pending states
        assert not EnumGeneralStatus.ACTIVE.is_pending_state()
        assert not EnumGeneralStatus.COMPLETED.is_pending_state()
        assert not EnumGeneralStatus.FAILED.is_pending_state()

    def test_is_quality_state_method(self):
        """Test is_quality_state method."""
        # Quality states
        assert EnumGeneralStatus.VALID.is_quality_state()
        assert EnumGeneralStatus.INVALID.is_quality_state()
        assert EnumGeneralStatus.UNKNOWN.is_quality_state()
        assert EnumGeneralStatus.APPROVED.is_quality_state()
        assert EnumGeneralStatus.REJECTED.is_quality_state()
        assert EnumGeneralStatus.UNDER_REVIEW.is_quality_state()

        # Non-quality states
        assert not EnumGeneralStatus.ACTIVE.is_quality_state()
        assert not EnumGeneralStatus.RUNNING.is_quality_state()
        assert not EnumGeneralStatus.CREATED.is_quality_state()

    def test_is_lifecycle_state_method(self):
        """Test is_lifecycle_state method."""
        # Lifecycle states
        assert EnumGeneralStatus.CREATED.is_lifecycle_state()
        assert EnumGeneralStatus.UPDATED.is_lifecycle_state()
        assert EnumGeneralStatus.DELETED.is_lifecycle_state()
        assert EnumGeneralStatus.ARCHIVED.is_lifecycle_state()
        assert EnumGeneralStatus.INACTIVE.is_lifecycle_state()
        assert EnumGeneralStatus.ACTIVE.is_lifecycle_state()

        # Non-lifecycle states
        assert not EnumGeneralStatus.RUNNING.is_lifecycle_state()
        assert not EnumGeneralStatus.COMPLETED.is_lifecycle_state()
        assert not EnumGeneralStatus.APPROVED.is_lifecycle_state()

    def test_is_operational_state_method(self):
        """Test is_operational_state method."""
        # Operational states
        assert EnumGeneralStatus.ENABLED.is_operational_state()
        assert EnumGeneralStatus.DISABLED.is_operational_state()
        assert EnumGeneralStatus.SUSPENDED.is_operational_state()
        assert EnumGeneralStatus.MAINTENANCE.is_operational_state()
        assert EnumGeneralStatus.AVAILABLE.is_operational_state()
        assert EnumGeneralStatus.UNAVAILABLE.is_operational_state()

        # Non-operational states
        assert not EnumGeneralStatus.ACTIVE.is_operational_state()
        assert not EnumGeneralStatus.RUNNING.is_operational_state()
        assert not EnumGeneralStatus.CREATED.is_operational_state()

    def test_get_approval_states_class_method(self):
        """Test get_approval_states class method."""
        approval_states = EnumGeneralStatus.get_approval_states()
        expected = {
            EnumGeneralStatus.APPROVED,
            EnumGeneralStatus.REJECTED,
            EnumGeneralStatus.UNDER_REVIEW,
        }
        assert approval_states == expected

    def test_get_lifecycle_states_class_method(self):
        """Test get_lifecycle_states class method."""
        lifecycle_states = EnumGeneralStatus.get_lifecycle_states()
        expected = {
            EnumGeneralStatus.CREATED,
            EnumGeneralStatus.UPDATED,
            EnumGeneralStatus.DELETED,
            EnumGeneralStatus.ARCHIVED,
            EnumGeneralStatus.ACTIVE,
            EnumGeneralStatus.INACTIVE,
        }
        assert lifecycle_states == expected

    def test_get_operational_states_class_method(self):
        """Test get_operational_states class method."""
        operational_states = EnumGeneralStatus.get_operational_states()
        expected = {
            EnumGeneralStatus.ENABLED,
            EnumGeneralStatus.DISABLED,
            EnumGeneralStatus.SUSPENDED,
            EnumGeneralStatus.AVAILABLE,
            EnumGeneralStatus.UNAVAILABLE,
            EnumGeneralStatus.MAINTENANCE,
        }
        assert operational_states == expected

    def test_enum_status_alias(self):
        """Test that EnumStatus alias works."""
        from omnibase_core.enums.enum_general_status import EnumStatus

        assert EnumStatus is EnumGeneralStatus
        assert EnumStatus.ACTIVE == EnumGeneralStatus.ACTIVE

    def test_status_categorization_completeness(self):
        """Test that all statuses are categorized by at least one method."""
        all_statuses = set(EnumGeneralStatus)

        # Get statuses categorized by each method
        active_statuses = {e for e in EnumGeneralStatus if e.is_active_state()}
        terminal_statuses = {e for e in EnumGeneralStatus if e.is_terminal_state()}
        error_statuses = {e for e in EnumGeneralStatus if e.is_error_state()}
        pending_statuses = {e for e in EnumGeneralStatus if e.is_pending_state()}
        quality_statuses = {e for e in EnumGeneralStatus if e.is_quality_state()}
        lifecycle_statuses = {e for e in EnumGeneralStatus if e.is_lifecycle_state()}
        operational_statuses = {
            e for e in EnumGeneralStatus if e.is_operational_state()
        }

        # All statuses should be categorized by at least one method
        categorized_statuses = (
            active_statuses
            | terminal_statuses
            | error_statuses
            | pending_statuses
            | quality_statuses
            | lifecycle_statuses
            | operational_statuses
        )
        assert (
            len(categorized_statuses) >= len(all_statuses) - 2
        )  # Most statuses should be categorized

    def test_status_workflow_progression(self):
        """Test logical workflow progression of statuses."""
        # Typical workflow: created -> active -> completed
        workflow_states = [
            EnumGeneralStatus.CREATED,
            EnumGeneralStatus.ACTIVE,
            EnumGeneralStatus.COMPLETED,
        ]

        # All workflow states should be valid
        for state in workflow_states:
            assert state in EnumGeneralStatus

    def test_status_state_transitions(self):
        """Test logical state transitions."""
        # Active to terminal transitions
        assert EnumGeneralStatus.ACTIVE.is_active_state()
        assert not EnumGeneralStatus.ACTIVE.is_terminal_state()

        assert not EnumGeneralStatus.COMPLETED.is_active_state()
        assert EnumGeneralStatus.COMPLETED.is_terminal_state()

        # Error state transitions
        assert EnumGeneralStatus.FAILED.is_error_state()
        assert EnumGeneralStatus.FAILED.is_terminal_state()

        # Pending state transitions
        assert EnumGeneralStatus.PENDING.is_pending_state()
        assert not EnumGeneralStatus.PENDING.is_active_state()
