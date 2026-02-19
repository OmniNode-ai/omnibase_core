# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumOperationStatus.

Tests all aspects of the operation status enum including:
- Enum value validation
- Status classification methods (terminal, active, successful)
- Base status conversion (to_base_status, from_base_status)
- String representation
- JSON serialization compatibility
- Pydantic integration
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_operation_status import EnumOperationStatus


@pytest.mark.unit
class TestEnumOperationStatus:
    """Test cases for EnumOperationStatus."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "SUCCESS": "success",
            "FAILED": "failed",
            "IN_PROGRESS": "in_progress",
            "CANCELLED": "cancelled",
            "PENDING": "pending",
            "TIMEOUT": "timeout",
        }

        for name, value in expected_values.items():
            status = getattr(EnumOperationStatus, name)
            assert status.value == value

    def test_string_value(self):
        """Test value attribute of enum values."""
        assert EnumOperationStatus.SUCCESS.value == "success"
        assert EnumOperationStatus.FAILED.value == "failed"
        assert EnumOperationStatus.IN_PROGRESS.value == "in_progress"
        assert EnumOperationStatus.PENDING.value == "pending"

    def test_is_terminal(self):
        """Test the is_terminal instance method."""
        # Terminal statuses
        terminal_statuses = [
            EnumOperationStatus.SUCCESS,
            EnumOperationStatus.FAILED,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.TIMEOUT,
        ]

        for status in terminal_statuses:
            assert status.is_terminal() is True

        # Non-terminal statuses
        non_terminal_statuses = [
            EnumOperationStatus.IN_PROGRESS,
            EnumOperationStatus.PENDING,
        ]

        for status in non_terminal_statuses:
            assert status.is_terminal() is False

    def test_is_active(self):
        """Test the is_active instance method."""
        # Active statuses
        active_statuses = [
            EnumOperationStatus.IN_PROGRESS,
            EnumOperationStatus.PENDING,
        ]

        for status in active_statuses:
            assert status.is_active() is True

        # Non-active statuses
        non_active_statuses = [
            EnumOperationStatus.SUCCESS,
            EnumOperationStatus.FAILED,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.TIMEOUT,
        ]

        for status in non_active_statuses:
            assert status.is_active() is False

    def test_is_successful(self):
        """Test the is_successful instance method."""
        # Only SUCCESS should return True
        assert EnumOperationStatus.SUCCESS.is_successful() is True

        # All other statuses should return False
        non_successful_statuses = [
            EnumOperationStatus.FAILED,
            EnumOperationStatus.IN_PROGRESS,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.PENDING,
            EnumOperationStatus.TIMEOUT,
        ]

        for status in non_successful_statuses:
            assert status.is_successful() is False

    def test_to_base_status(self):
        """Test to_base_status conversion method."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # Test all mappings
        assert EnumOperationStatus.SUCCESS.to_base_status() == EnumBaseStatus.COMPLETED
        assert EnumOperationStatus.FAILED.to_base_status() == EnumBaseStatus.FAILED
        assert (
            EnumOperationStatus.IN_PROGRESS.to_base_status() == EnumBaseStatus.RUNNING
        )
        assert EnumOperationStatus.CANCELLED.to_base_status() == EnumBaseStatus.INACTIVE
        assert EnumOperationStatus.PENDING.to_base_status() == EnumBaseStatus.PENDING
        assert EnumOperationStatus.TIMEOUT.to_base_status() == EnumBaseStatus.FAILED

    def test_from_base_status(self):
        """Test from_base_status class method."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # Test valid conversions
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.COMPLETED)
            == EnumOperationStatus.SUCCESS
        )
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.FAILED)
            == EnumOperationStatus.FAILED
        )
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.RUNNING)
            == EnumOperationStatus.IN_PROGRESS
        )
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.INACTIVE)
            == EnumOperationStatus.CANCELLED
        )
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.PENDING)
            == EnumOperationStatus.PENDING
        )
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.ACTIVE)
            == EnumOperationStatus.IN_PROGRESS
        )
        assert (
            EnumOperationStatus.from_base_status(EnumBaseStatus.UNKNOWN)
            == EnumOperationStatus.PENDING
        )

    def test_from_base_status_invalid(self):
        """Test from_base_status raises ValueError for unmapped values."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # VALID and INVALID don't have mappings, should raise ValueError
        with pytest.raises(ValueError):
            EnumOperationStatus.from_base_status(EnumBaseStatus.VALID)

        with pytest.raises(ValueError):
            EnumOperationStatus.from_base_status(EnumBaseStatus.INVALID)

    def test_base_status_roundtrip(self):
        """Test roundtrip conversion base -> operation -> base."""
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # These base statuses should roundtrip
        roundtrip_statuses = [
            EnumBaseStatus.PENDING,
            EnumBaseStatus.RUNNING,
            EnumBaseStatus.FAILED,
        ]

        for base_status in roundtrip_statuses:
            op_status = EnumOperationStatus.from_base_status(base_status)
            back_to_base = op_status.to_base_status()
            assert back_to_base == base_status, (
                f"Roundtrip failed for {base_status}: "
                f"got {back_to_base} via {op_status}"
            )

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumOperationStatus.SUCCESS == EnumOperationStatus.SUCCESS
        assert EnumOperationStatus.FAILED != EnumOperationStatus.SUCCESS
        assert EnumOperationStatus.IN_PROGRESS == EnumOperationStatus.IN_PROGRESS

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_statuses = [
            EnumOperationStatus.SUCCESS,
            EnumOperationStatus.FAILED,
            EnumOperationStatus.IN_PROGRESS,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.PENDING,
            EnumOperationStatus.TIMEOUT,
        ]

        for status in all_statuses:
            assert status in EnumOperationStatus

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        statuses = list(EnumOperationStatus)
        assert len(statuses) == 6

        status_values = [status.value for status in statuses]
        expected_values = [
            "success",
            "failed",
            "in_progress",
            "cancelled",
            "pending",
            "timeout",
        ]

        assert set(status_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        status = EnumOperationStatus.IN_PROGRESS
        json_str = json.dumps(status, default=str)
        assert json_str == '"in_progress"'

        # Test in dictionary
        data = {"operation_status": EnumOperationStatus.SUCCESS}
        json_str = json.dumps(data, default=str)
        assert '"operation_status": "success"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class OperationModel(BaseModel):
            status: EnumOperationStatus

        # Test valid enum assignment
        model = OperationModel(status=EnumOperationStatus.SUCCESS)
        assert model.status == EnumOperationStatus.SUCCESS

        # Test string assignment (should work due to str inheritance)
        model = OperationModel(status="in_progress")
        assert model.status == EnumOperationStatus.IN_PROGRESS

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            OperationModel(status="invalid_status")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class OperationModel(BaseModel):
            status: EnumOperationStatus

        model = OperationModel(status=EnumOperationStatus.FAILED)

        # Test dict serialization
        model_dict = model.model_dump()
        assert model_dict == {"status": "failed"}

        # Test JSON serialization
        json_str = model.model_dump_json()
        assert json_str == '{"status":"failed"}'

    def test_operation_lifecycle_logic(self):
        """Test operation lifecycle state transitions and logic."""
        # Test that active and terminal states are mutually exclusive
        for status in EnumOperationStatus:
            is_active = status.is_active()
            is_terminal = status.is_terminal()

            # A status cannot be both active and terminal
            assert not (is_active and is_terminal), (
                f"{status} cannot be both active and terminal"
            )

        # Test that all statuses are either active or terminal
        for status in EnumOperationStatus:
            is_active = status.is_active()
            is_terminal = status.is_terminal()

            assert is_active or is_terminal, (
                f"{status} must be either active or terminal"
            )

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable (as string values)
        data = {"status": EnumOperationStatus.TIMEOUT.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "status: timeout" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["status"] == "timeout"

    def test_is_terminal_edge_cases(self):
        """Test is_terminal with edge cases and boundary conditions.

        Verifies nuanced terminal state semantics for operation status:
        - TIMEOUT is terminal (forced termination from time limit)
        - CANCELLED is terminal (intentional termination)
        - IN_PROGRESS is NOT terminal (operation still executing)
        """
        # TIMEOUT is terminal (error condition)
        assert EnumOperationStatus.TIMEOUT.is_terminal() is True
        assert EnumOperationStatus.TIMEOUT.is_successful() is False

        # CANCELLED is terminal but neither success nor standard failure
        assert EnumOperationStatus.CANCELLED.is_terminal() is True
        assert EnumOperationStatus.CANCELLED.is_successful() is False

        # IN_PROGRESS must not be terminal
        assert EnumOperationStatus.IN_PROGRESS.is_terminal() is False
        assert EnumOperationStatus.IN_PROGRESS.is_active() is True

    def test_is_terminal_mutual_exclusivity(self):
        """Test that terminal and active states are mutually exclusive.

        Every operation status must be either terminal or active, never both.
        This is a fundamental invariant of operation lifecycle semantics.
        """
        for status in EnumOperationStatus:
            is_terminal = status.is_terminal()
            is_active = status.is_active()

            # XOR: exactly one must be true
            assert is_terminal != is_active, (
                f"{status} violates mutual exclusivity: "
                f"is_terminal={is_terminal}, is_active={is_active}"
            )

    def test_is_terminal_completeness(self):
        """Test that all status values are categorized by is_terminal.

        Every status must be either terminal or non-terminal (active).
        This ensures no status values are left uncategorized.
        """
        terminal_count = sum(1 for s in EnumOperationStatus if s.is_terminal())
        active_count = sum(1 for s in EnumOperationStatus if s.is_active())

        # All statuses should be accounted for
        assert terminal_count + active_count == len(EnumOperationStatus)

        # Expected counts based on the enum definition
        assert terminal_count == 4  # SUCCESS, FAILED, CANCELLED, TIMEOUT
        assert active_count == 2  # IN_PROGRESS, PENDING

    def test_roundtrip_serialization_all_values(self):
        """Test roundtrip serialization for all enum values.

        Ensures str(enum) -> Enum(str) works for every value.
        """
        for status in EnumOperationStatus:
            # String roundtrip
            serialized = str(status)
            deserialized = EnumOperationStatus(serialized)
            assert deserialized == status, (
                f"String roundtrip failed for {status}: "
                f"serialized={serialized}, deserialized={deserialized}"
            )

            # Value roundtrip
            value = status.value
            reconstructed = EnumOperationStatus(value)
            assert reconstructed == status, (
                f"Value roundtrip failed for {status}: "
                f"value={value}, reconstructed={reconstructed}"
            )

    def test_inactive_mapping_via_base_status(self):
        """Test that INACTIVE base status maps correctly to CANCELLED.

        EnumBaseStatus.INACTIVE represents intentional deactivation,
        which maps to CANCELLED in operation context (intentional termination).
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # INACTIVE -> CANCELLED
        result = EnumOperationStatus.from_base_status(EnumBaseStatus.INACTIVE)
        assert result == EnumOperationStatus.CANCELLED

        # And CANCELLED -> INACTIVE roundtrip
        back_to_base = result.to_base_status()
        assert back_to_base == EnumBaseStatus.INACTIVE

    def test_base_status_roundtrip_extended(self):
        """Test extended roundtrip conversions including INACTIVE.

        Verifies that base status conversions are consistent and
        that INACTIVE (a key lifecycle state) roundtrips correctly.
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # Extended roundtrip tests including all mapped base statuses
        roundtrip_statuses = [
            (EnumBaseStatus.PENDING, EnumOperationStatus.PENDING),
            (EnumBaseStatus.RUNNING, EnumOperationStatus.IN_PROGRESS),
            (EnumBaseStatus.FAILED, EnumOperationStatus.FAILED),
            (EnumBaseStatus.INACTIVE, EnumOperationStatus.CANCELLED),
            (EnumBaseStatus.ACTIVE, EnumOperationStatus.IN_PROGRESS),
            (EnumBaseStatus.UNKNOWN, EnumOperationStatus.PENDING),
        ]

        for base_status, expected_op_status in roundtrip_statuses:
            op_status = EnumOperationStatus.from_base_status(base_status)
            assert op_status == expected_op_status, (
                f"Mapping failed for {base_status}: "
                f"expected={expected_op_status}, actual={op_status}"
            )

    def test_all_base_status_mappings(self):
        """Test all valid base status to operation status mappings.

        Ensures complete coverage of from_base_status method.
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # All valid mappings
        valid_mappings = {
            EnumBaseStatus.COMPLETED: EnumOperationStatus.SUCCESS,
            EnumBaseStatus.FAILED: EnumOperationStatus.FAILED,
            EnumBaseStatus.RUNNING: EnumOperationStatus.IN_PROGRESS,
            EnumBaseStatus.INACTIVE: EnumOperationStatus.CANCELLED,
            EnumBaseStatus.PENDING: EnumOperationStatus.PENDING,
            EnumBaseStatus.ACTIVE: EnumOperationStatus.IN_PROGRESS,
            EnumBaseStatus.UNKNOWN: EnumOperationStatus.PENDING,
        }

        for base_status, expected in valid_mappings.items():
            result = EnumOperationStatus.from_base_status(base_status)
            assert result == expected
