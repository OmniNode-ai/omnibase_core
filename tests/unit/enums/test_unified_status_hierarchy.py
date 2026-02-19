# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test Unified Status Enum Hierarchy.

Validates the new unified status enum hierarchy works correctly and provides
proper migration paths from old conflicting enums.
"""

import pytest

from omnibase_core.enums.enum_base_status import EnumBaseStatus
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_function_lifecycle_status import (
    EnumFunctionLifecycleStatus,
    EnumFunctionStatus,
    EnumMetadataNodeStatus,
)
from omnibase_core.enums.enum_general_status import EnumGeneralStatus, EnumStatus
from omnibase_core.models.core.model_status_migrator import ModelEnumStatusMigrator
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.validation.model_status_migration_validator import (
    ModelEnumStatusMigrationValidator,
)


@pytest.mark.unit
class TestBaseStatus:
    """Test base status enum functionality."""

    def test_base_status_values(self):
        """Test base status contains expected values."""
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
        actual_values = {status.value for status in EnumBaseStatus}
        assert actual_values == expected_values

    def test_base_status_methods(self):
        """Test base status utility methods."""
        # Test active states
        assert EnumBaseStatus.ACTIVE.is_active_state()
        assert EnumBaseStatus.RUNNING.is_active_state()
        assert EnumBaseStatus.PENDING.is_active_state()
        assert not EnumBaseStatus.FAILED.is_active_state()

        # Test terminal states
        assert EnumBaseStatus.COMPLETED.is_terminal_state()
        assert EnumBaseStatus.FAILED.is_terminal_state()
        assert EnumBaseStatus.INACTIVE.is_terminal_state()
        assert not EnumBaseStatus.RUNNING.is_terminal_state()

        # Test error states
        assert EnumBaseStatus.FAILED.is_error_state()
        assert EnumBaseStatus.INVALID.is_error_state()
        assert not EnumBaseStatus.COMPLETED.is_error_state()

        # Test pending states
        assert EnumBaseStatus.PENDING.is_pending_state()
        assert EnumBaseStatus.RUNNING.is_pending_state()
        assert EnumBaseStatus.UNKNOWN.is_pending_state()
        assert not EnumBaseStatus.COMPLETED.is_pending_state()


@pytest.mark.unit
class TestExecutionStatus:
    """Test canonical execution status functionality (OMN-1310)."""

    def test_execution_status_values(self):
        """Test execution status contains all required values."""
        expected_values = {
            "pending",
            "running",
            "completed",
            "success",
            "failed",
            "skipped",
            "cancelled",
            "timeout",
            "partial",
        }
        actual_values = {status.value for status in EnumExecutionStatus}
        assert actual_values == expected_values

    def test_execution_status_base_overlap(self):
        """Test execution status shares common values with base status."""
        # These values should match base status
        assert EnumExecutionStatus.PENDING.value == EnumBaseStatus.PENDING.value
        assert EnumExecutionStatus.RUNNING.value == EnumBaseStatus.RUNNING.value
        assert EnumExecutionStatus.COMPLETED.value == EnumBaseStatus.COMPLETED.value
        assert EnumExecutionStatus.FAILED.value == EnumBaseStatus.FAILED.value

    def test_execution_specific_values(self):
        """Test execution-specific status values."""
        execution_specific = {
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.SKIPPED,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.PARTIAL,
        }
        for status in execution_specific:
            assert status.value in [
                "success",
                "skipped",
                "cancelled",
                "timeout",
                "partial",
            ]

    def test_base_status_conversion(self):
        """Test conversion to base status."""
        # Direct base values should map directly
        assert EnumExecutionStatus.PENDING.to_base_status() == EnumBaseStatus.PENDING
        assert EnumExecutionStatus.RUNNING.to_base_status() == EnumBaseStatus.RUNNING
        assert (
            EnumExecutionStatus.COMPLETED.to_base_status() == EnumBaseStatus.COMPLETED
        )
        assert EnumExecutionStatus.FAILED.to_base_status() == EnumBaseStatus.FAILED

        # Execution-specific values should map to appropriate base
        assert EnumExecutionStatus.SUCCESS.to_base_status() == EnumBaseStatus.COMPLETED
        assert EnumExecutionStatus.TIMEOUT.to_base_status() == EnumBaseStatus.FAILED
        assert EnumExecutionStatus.CANCELLED.to_base_status() == EnumBaseStatus.INACTIVE
        assert EnumExecutionStatus.SKIPPED.to_base_status() == EnumBaseStatus.INACTIVE
        assert EnumExecutionStatus.PARTIAL.to_base_status() == EnumBaseStatus.COMPLETED

    def test_execution_status_methods(self):
        """Test execution status utility methods."""
        # Test terminal states
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.SUCCESS)
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.FAILED)
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.TIMEOUT)
        assert EnumExecutionStatus.is_terminal(EnumExecutionStatus.PARTIAL)
        assert not EnumExecutionStatus.is_terminal(EnumExecutionStatus.RUNNING)
        assert not EnumExecutionStatus.is_terminal(EnumExecutionStatus.PENDING)

        # Test active states
        assert EnumExecutionStatus.is_active(EnumExecutionStatus.RUNNING)
        assert EnumExecutionStatus.is_active(EnumExecutionStatus.PENDING)
        assert not EnumExecutionStatus.is_active(EnumExecutionStatus.COMPLETED)
        assert not EnumExecutionStatus.is_active(EnumExecutionStatus.FAILED)

        # Test successful states
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.SUCCESS)
        assert EnumExecutionStatus.is_successful(EnumExecutionStatus.COMPLETED)
        assert not EnumExecutionStatus.is_successful(EnumExecutionStatus.FAILED)

        # Test failure states
        assert EnumExecutionStatus.is_failure(EnumExecutionStatus.FAILED)
        assert EnumExecutionStatus.is_failure(EnumExecutionStatus.TIMEOUT)
        assert not EnumExecutionStatus.is_failure(EnumExecutionStatus.SUCCESS)
        assert not EnumExecutionStatus.is_failure(EnumExecutionStatus.CANCELLED)

        # Test running state
        assert EnumExecutionStatus.is_running(EnumExecutionStatus.RUNNING)
        assert not EnumExecutionStatus.is_running(EnumExecutionStatus.PENDING)

        # Test cancelled state
        assert EnumExecutionStatus.is_cancelled(EnumExecutionStatus.CANCELLED)
        assert not EnumExecutionStatus.is_cancelled(EnumExecutionStatus.FAILED)

        # Test partial state
        assert EnumExecutionStatus.is_partial(EnumExecutionStatus.PARTIAL)
        assert not EnumExecutionStatus.is_partial(EnumExecutionStatus.SUCCESS)

        # Test skipped state
        assert EnumExecutionStatus.is_skipped(EnumExecutionStatus.SKIPPED)
        assert not EnumExecutionStatus.is_skipped(EnumExecutionStatus.SUCCESS)


@pytest.mark.unit
class TestFunctionLifecycleStatus:
    """Test function lifecycle status functionality."""

    def test_lifecycle_status_values(self):
        """Test lifecycle status contains expected values."""
        expected_values = {
            "active",
            "inactive",
            "deprecated",
            "disabled",
            "experimental",
            "maintenance",
            "stable",
            "beta",
            "alpha",
        }
        actual_values = {status.value for status in EnumFunctionLifecycleStatus}
        assert actual_values == expected_values

    def test_lifecycle_status_methods(self):
        """Test lifecycle status utility methods."""
        # Test availability
        assert EnumFunctionLifecycleStatus.is_available(
            EnumFunctionLifecycleStatus.ACTIVE,
        )
        assert EnumFunctionLifecycleStatus.is_available(
            EnumFunctionLifecycleStatus.EXPERIMENTAL,
        )
        assert not EnumFunctionLifecycleStatus.is_available(
            EnumFunctionLifecycleStatus.DISABLED,
        )

        # Test production ready
        assert EnumFunctionLifecycleStatus.is_production_ready(
            EnumFunctionLifecycleStatus.ACTIVE,
        )
        assert EnumFunctionLifecycleStatus.is_production_ready(
            EnumFunctionLifecycleStatus.STABLE,
        )
        assert not EnumFunctionLifecycleStatus.is_production_ready(
            EnumFunctionLifecycleStatus.BETA,
        )

        # Test testing phase
        assert EnumFunctionLifecycleStatus.is_testing_phase(
            EnumFunctionLifecycleStatus.ALPHA,
        )
        assert EnumFunctionLifecycleStatus.is_testing_phase(
            EnumFunctionLifecycleStatus.BETA,
        )
        assert not EnumFunctionLifecycleStatus.is_testing_phase(
            EnumFunctionLifecycleStatus.STABLE,
        )

    def test_base_status_conversion(self):
        """Test conversion to base status."""
        assert (
            EnumFunctionLifecycleStatus.ACTIVE.to_base_status() == EnumBaseStatus.ACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.DISABLED.to_base_status()
            == EnumBaseStatus.INACTIVE
        )
        assert (
            EnumFunctionLifecycleStatus.EXPERIMENTAL.to_base_status()
            == EnumBaseStatus.ACTIVE
        )

    def test_backward_compatibility_aliases(self):
        """Test backward compatibility aliases."""
        # EnumFunctionStatus alias
        assert EnumFunctionStatus.ACTIVE == EnumFunctionLifecycleStatus.ACTIVE
        assert EnumFunctionStatus.DEPRECATED == EnumFunctionLifecycleStatus.DEPRECATED

        # EnumMetadataNodeStatus alias
        assert EnumMetadataNodeStatus.STABLE == EnumFunctionLifecycleStatus.STABLE
        assert EnumMetadataNodeStatus.BETA == EnumFunctionLifecycleStatus.BETA


@pytest.mark.unit
class TestGeneralStatus:
    """Test general status functionality."""

    def test_general_status_comprehensive(self):
        """Test general status contains comprehensive values."""
        # Should include base values
        assert EnumGeneralStatus.ACTIVE.value == EnumBaseStatus.ACTIVE.value
        assert EnumGeneralStatus.PENDING.value == EnumBaseStatus.PENDING.value

        # Should include extended values
        extended_values = {
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
        general_values = {status.value for status in EnumGeneralStatus}
        assert extended_values.issubset(general_values)

    def test_general_status_categorization(self):
        """Test general status categorization methods."""
        # Test lifecycle states
        assert EnumGeneralStatus.CREATED.is_lifecycle_state()
        assert EnumGeneralStatus.UPDATED.is_lifecycle_state()
        assert not EnumGeneralStatus.APPROVED.is_lifecycle_state()

        # Test approval states
        approval_states = EnumGeneralStatus.get_approval_states()
        assert EnumGeneralStatus.APPROVED in approval_states
        assert EnumGeneralStatus.REJECTED in approval_states
        assert EnumGeneralStatus.UNDER_REVIEW in approval_states

        # Test operational states
        operational_states = EnumGeneralStatus.get_operational_states()
        assert EnumGeneralStatus.ENABLED in operational_states
        assert EnumGeneralStatus.MAINTENANCE in operational_states

    def test_backward_compatibility(self):
        """Test backward compatibility with original EnumStatus."""
        assert EnumStatus.ACTIVE == EnumGeneralStatus.ACTIVE
        assert EnumStatus.PROCESSING == EnumGeneralStatus.PROCESSING


@pytest.mark.unit
class TestStatusMigration:
    """Test status migration utilities."""

    def test_migration_validation(self):
        """Test status migration validation."""
        migrator = ModelEnumStatusMigrator()

        # Test valid migrations
        assert migrator.migrate_general_status("active") == EnumGeneralStatus.ACTIVE
        assert (
            migrator.migrate_execution_status("pending") == EnumExecutionStatus.PENDING
        )
        assert (
            migrator.migrate_function_status("deprecated")
            == EnumFunctionLifecycleStatus.DEPRECATED
        )

        # Test invalid migrations
        with pytest.raises(OnexError):
            migrator.migrate_general_status("invalid_value")

    def test_migration_validator(self):
        """Test migration validation functionality."""
        validator = ModelEnumStatusMigrationValidator()

        # Test valid value validation
        result = validator.validate_value_migration(
            "active",
            "EnumStatus",
            EnumGeneralStatus,
        )
        assert result["success"]
        assert result["migrated_value"] == "active"

        # Test conflict detection
        conflicts = validator.find_enum_conflicts()
        # Should detect the known conflicts
        assert "completed" in conflicts
        assert "failed" in conflicts
        assert "active" in conflicts
        assert len(conflicts["completed"]) >= 3  # At least 3 enums have 'completed'

    def test_migration_report(self):
        """Test migration report generation."""
        validator = ModelEnumStatusMigrationValidator()
        report = validator.generate_migration_report()

        assert "summary" in report
        assert "conflicts" in report
        assert "migration_mapping" in report
        assert "recommendations" in report

        # Should identify the main conflicts
        assert report["summary"]["total_conflicts"] > 0
        assert "completed" in report["summary"]["conflicting_values"]


@pytest.mark.unit
class TestCrossEnumCompatibility:
    """Test compatibility across unified enum hierarchy."""

    def test_base_status_universal_operations(self):
        """Test base status can be used for universal operations."""
        # All domain enums should convert to base status
        execution_status = EnumExecutionStatus.SUCCESS
        function_status = EnumFunctionLifecycleStatus.ACTIVE
        general_status = EnumGeneralStatus.APPROVED

        # All should convert to base status
        exec_base = execution_status.to_base_status()
        func_base = function_status.to_base_status()
        gen_base = general_status.to_base_status()

        assert isinstance(exec_base, EnumBaseStatus)
        assert isinstance(func_base, EnumBaseStatus)
        assert isinstance(gen_base, EnumBaseStatus)

    def test_cross_domain_status_comparison(self):
        """Test cross-domain status comparisons via base status."""
        # Different domain statuses that should map to same base
        execution_success = EnumExecutionStatus.SUCCESS
        general_completed = EnumGeneralStatus.COMPLETED

        # Should both map to COMPLETED base status
        assert execution_success.to_base_status() == EnumBaseStatus.COMPLETED
        assert general_completed.to_base_status() == EnumBaseStatus.COMPLETED

        # Therefore should be equivalent at base level
        assert execution_success.to_base_status() == general_completed.to_base_status()

    def test_no_value_conflicts_in_hierarchy(self):
        """Test that the unified hierarchy eliminates value conflicts."""
        # Get all values from each enum
        base_values = {s.value for s in EnumBaseStatus}
        execution_values = {s.value for s in EnumExecutionStatus}
        function_values = {s.value for s in EnumFunctionLifecycleStatus}
        general_values = {s.value for s in EnumGeneralStatus}

        # Base values should be properly inherited
        base_in_execution = base_values.intersection(execution_values)
        base_in_function = base_values.intersection(function_values)
        base_in_general = base_values.intersection(general_values)

        # Should have some overlap with base (inheritance)
        assert len(base_in_execution) > 0
        assert len(base_in_function) > 0
        assert len(base_in_general) > 0

        # Domain-specific values should not conflict with each other
        execution_specific = execution_values - base_values
        function_specific = function_values - base_values
        general_specific = general_values - base_values

        # No conflicts between domain-specific values
        assert len(execution_specific.intersection(function_specific)) == 0
        # General status intentionally includes some common values, so we don't test it the same way
