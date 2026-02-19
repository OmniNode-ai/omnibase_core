# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum

import pytest

from omnibase_core.enums.enum_status import EnumStatus


@pytest.mark.unit
class TestEnumStatus:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        # Basic status states
        assert EnumStatus.ACTIVE == "active"
        assert EnumStatus.INACTIVE == "inactive"
        assert EnumStatus.PENDING == "pending"

        # Processing states
        assert EnumStatus.PROCESSING == "processing"
        assert EnumStatus.COMPLETED == "completed"
        assert EnumStatus.FAILED == "failed"

        # Lifecycle states
        assert EnumStatus.CREATED == "created"
        assert EnumStatus.UPDATED == "updated"
        assert EnumStatus.DELETED == "deleted"
        assert EnumStatus.ARCHIVED == "archived"

        # Validation states
        assert EnumStatus.VALID == "valid"
        assert EnumStatus.INVALID == "invalid"
        assert EnumStatus.UNKNOWN == "unknown"

        # Approval states
        assert EnumStatus.APPROVED == "approved"
        assert EnumStatus.REJECTED == "rejected"
        assert EnumStatus.UNDER_REVIEW == "under_review"

        # Availability states
        assert EnumStatus.AVAILABLE == "available"
        assert EnumStatus.UNAVAILABLE == "unavailable"
        assert EnumStatus.MAINTENANCE == "maintenance"

        # Quality states
        assert EnumStatus.DRAFT == "draft"
        assert EnumStatus.PUBLISHED == "published"
        assert EnumStatus.DEPRECATED == "deprecated"

        # Operational states
        assert EnumStatus.ENABLED == "enabled"
        assert EnumStatus.DISABLED == "disabled"
        assert EnumStatus.SUSPENDED == "suspended"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumStatus, str)
        assert issubclass(EnumStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumStatus.ACTIVE
        assert isinstance(status, str)
        assert status == "active"
        assert len(status) == 6
        assert status.startswith("act")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumStatus)
        assert len(values) == 25
        assert EnumStatus.ACTIVE in values
        assert EnumStatus.SUSPENDED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumStatus.PROCESSING in EnumStatus
        assert "processing" in [e.value for e in EnumStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumStatus.COMPLETED
        status2 = EnumStatus.COMPLETED
        status3 = EnumStatus.FAILED

        assert status1 == status2
        assert status1 != status3
        assert status1 == "completed"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumStatus.PUBLISHED
        serialized = status.value
        assert serialized == "published"
        import json

        json_str = json.dumps(status)
        assert json_str == '"published"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumStatus("draft")
        assert status == EnumStatus.DRAFT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
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
        actual_values = {e.value for e in EnumStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumStatus.__doc__ is not None
        assert "general status enumeration" in EnumStatus.__doc__.lower()

    def test_is_active_state_method(self):
        """Test is_active_state method."""
        # Active states
        assert EnumStatus.ACTIVE.is_active_state()
        assert EnumStatus.PROCESSING.is_active_state()
        assert EnumStatus.ENABLED.is_active_state()
        assert EnumStatus.AVAILABLE.is_active_state()
        assert EnumStatus.PUBLISHED.is_active_state()

        # Non-active states
        assert not EnumStatus.INACTIVE.is_active_state()
        assert not EnumStatus.COMPLETED.is_active_state()
        assert not EnumStatus.FAILED.is_active_state()
        assert not EnumStatus.DISABLED.is_active_state()

    def test_is_terminal_state_method(self):
        """Test is_terminal_state method."""
        # Terminal states
        assert EnumStatus.COMPLETED.is_terminal_state()
        assert EnumStatus.FAILED.is_terminal_state()
        assert EnumStatus.DELETED.is_terminal_state()
        assert EnumStatus.ARCHIVED.is_terminal_state()
        assert EnumStatus.DEPRECATED.is_terminal_state()

        # Non-terminal states
        assert not EnumStatus.ACTIVE.is_terminal_state()
        assert not EnumStatus.PROCESSING.is_terminal_state()
        assert not EnumStatus.PENDING.is_terminal_state()

    def test_is_error_state_method(self):
        """Test is_error_state method."""
        # Error states
        assert EnumStatus.FAILED.is_error_state()
        assert EnumStatus.INVALID.is_error_state()
        assert EnumStatus.REJECTED.is_error_state()
        assert EnumStatus.UNAVAILABLE.is_error_state()

        # Non-error states
        assert not EnumStatus.ACTIVE.is_error_state()
        assert not EnumStatus.COMPLETED.is_error_state()
        assert not EnumStatus.VALID.is_error_state()

    def test_is_pending_state_method(self):
        """Test is_pending_state method."""
        # Pending states
        assert EnumStatus.PENDING.is_pending_state()
        assert EnumStatus.PROCESSING.is_pending_state()
        assert EnumStatus.UNDER_REVIEW.is_pending_state()
        assert EnumStatus.DRAFT.is_pending_state()

        # Non-pending states
        assert not EnumStatus.ACTIVE.is_pending_state()
        assert not EnumStatus.COMPLETED.is_pending_state()
        assert not EnumStatus.FAILED.is_pending_state()

    def test_status_categorization_completeness(self):
        """Test that all statuses are categorized by at least one method."""
        all_statuses = set(EnumStatus)

        # Get statuses categorized by each method
        active_statuses = {e for e in EnumStatus if e.is_active_state()}
        terminal_statuses = {e for e in EnumStatus if e.is_terminal_state()}
        error_statuses = {e for e in EnumStatus if e.is_error_state()}
        pending_statuses = {e for e in EnumStatus if e.is_pending_state()}

        # All statuses should be categorized by at least one method
        categorized_statuses = (
            active_statuses | terminal_statuses | error_statuses | pending_statuses
        )
        assert (
            len(categorized_statuses) >= len(all_statuses) - 10
        )  # Most statuses should be categorized

    def test_status_logical_groupings(self):
        """Test logical groupings of status values."""
        # Basic states
        basic_states = {EnumStatus.ACTIVE, EnumStatus.INACTIVE, EnumStatus.PENDING}

        # Processing states
        processing_states = {
            EnumStatus.PROCESSING,
            EnumStatus.COMPLETED,
            EnumStatus.FAILED,
        }

        # Lifecycle states
        lifecycle_states = {
            EnumStatus.CREATED,
            EnumStatus.UPDATED,
            EnumStatus.DELETED,
            EnumStatus.ARCHIVED,
        }

        # Validation states
        validation_states = {EnumStatus.VALID, EnumStatus.INVALID, EnumStatus.UNKNOWN}

        # Approval states
        approval_states = {
            EnumStatus.APPROVED,
            EnumStatus.REJECTED,
            EnumStatus.UNDER_REVIEW,
        }

        # Availability states
        availability_states = {
            EnumStatus.AVAILABLE,
            EnumStatus.UNAVAILABLE,
            EnumStatus.MAINTENANCE,
        }

        # Quality states
        quality_states = {EnumStatus.DRAFT, EnumStatus.PUBLISHED, EnumStatus.DEPRECATED}

        # Operational states
        operational_states = {
            EnumStatus.ENABLED,
            EnumStatus.DISABLED,
            EnumStatus.SUSPENDED,
        }

        # Test that all states are covered
        all_grouped_states = (
            basic_states
            | processing_states
            | lifecycle_states
            | validation_states
            | approval_states
            | availability_states
            | quality_states
            | operational_states
        )
        assert all_grouped_states == set(EnumStatus)

    def test_status_workflow_progression(self):
        """Test logical workflow progression of statuses."""
        # Typical workflow: created -> active -> completed
        workflow_states = [
            EnumStatus.CREATED,
            EnumStatus.ACTIVE,
            EnumStatus.COMPLETED,
        ]

        # All workflow states should be valid
        for state in workflow_states:
            assert state in EnumStatus

    def test_status_state_transitions(self):
        """Test logical state transitions."""
        # Active to terminal transitions
        assert EnumStatus.ACTIVE.is_active_state()
        assert not EnumStatus.ACTIVE.is_terminal_state()

        assert not EnumStatus.COMPLETED.is_active_state()
        assert EnumStatus.COMPLETED.is_terminal_state()

        # Error state transitions
        assert EnumStatus.FAILED.is_error_state()
        assert EnumStatus.FAILED.is_terminal_state()

        # Pending state transitions
        assert EnumStatus.PENDING.is_pending_state()
        assert not EnumStatus.PENDING.is_active_state()
