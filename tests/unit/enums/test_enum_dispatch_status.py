# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumDispatchStatus.

Tests all aspects of the dispatch status enum including:
- Enum value validation
- Status classification methods (is_terminal, is_successful, is_error, requires_retry)
- Description helper
- String representation
- JSON serialization compatibility
- Pydantic integration
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus


@pytest.mark.unit
class TestEnumDispatchStatus:
    """Test cases for EnumDispatchStatus."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "SUCCESS": "success",
            "ROUTED": "routed",
            "NO_HANDLER": "no_handler",
            "HANDLER_ERROR": "handler_error",
            "TIMEOUT": "timeout",
            "INVALID_MESSAGE": "invalid_message",
            "PUBLISH_FAILED": "publish_failed",
            "SKIPPED": "skipped",
        }

        for name, value in expected_values.items():
            status = getattr(EnumDispatchStatus, name)
            assert status.value == value

    def test_enum_count(self):
        """Test expected number of enum values."""
        assert len(EnumDispatchStatus) == 8

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumDispatchStatus.SUCCESS) == "success"
        assert str(EnumDispatchStatus.HANDLER_ERROR) == "handler_error"
        assert str(EnumDispatchStatus.TIMEOUT) == "timeout"

    def test_is_terminal(self):
        """Test the is_terminal instance method."""
        # Terminal statuses (operation has completed)
        terminal_statuses = [
            EnumDispatchStatus.SUCCESS,
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
            EnumDispatchStatus.SKIPPED,
        ]

        for status in terminal_statuses:
            assert status.is_terminal() is True

        # Non-terminal statuses
        non_terminal_statuses = [
            EnumDispatchStatus.ROUTED,
        ]

        for status in non_terminal_statuses:
            assert status.is_terminal() is False

    def test_is_terminal_edge_cases(self):
        """Test is_terminal with edge cases and boundary conditions."""
        # ROUTED is the only non-terminal state (message routed but not executed)
        assert EnumDispatchStatus.ROUTED.is_terminal() is False

        # SKIPPED is terminal even though it's not an error or success
        assert EnumDispatchStatus.SKIPPED.is_terminal() is True

        # All error states should be terminal
        error_states = [
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
        ]
        for status in error_states:
            assert status.is_terminal() is True
            assert status.is_error() is True

    def test_is_successful(self):
        """Test the is_successful instance method."""
        # Only SUCCESS should return True
        assert EnumDispatchStatus.SUCCESS.is_successful() is True

        # All other statuses should return False
        for status in EnumDispatchStatus:
            if status != EnumDispatchStatus.SUCCESS:
                assert status.is_successful() is False

    def test_is_error(self):
        """Test the is_error instance method."""
        # Error statuses
        error_statuses = [
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
        ]

        for status in error_statuses:
            assert status.is_error() is True

        # Non-error statuses
        non_error_statuses = [
            EnumDispatchStatus.SUCCESS,
            EnumDispatchStatus.ROUTED,
            EnumDispatchStatus.SKIPPED,
        ]

        for status in non_error_statuses:
            assert status.is_error() is False

    def test_requires_retry(self):
        """Test the requires_retry instance method."""
        # Transient failures that should be retried
        retry_statuses = [
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.PUBLISH_FAILED,
        ]

        for status in retry_statuses:
            assert status.requires_retry() is True

        # Permanent failures or non-failures that should not be retried
        no_retry_statuses = [
            EnumDispatchStatus.SUCCESS,
            EnumDispatchStatus.ROUTED,
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.SKIPPED,
        ]

        for status in no_retry_statuses:
            assert status.requires_retry() is False

    def test_get_description(self):
        """Test the get_description class method."""
        # Test specific descriptions
        assert (
            "successfully"
            in EnumDispatchStatus.get_description(EnumDispatchStatus.SUCCESS).lower()
        )
        assert (
            "handler"
            in EnumDispatchStatus.get_description(EnumDispatchStatus.NO_HANDLER).lower()
        )
        assert (
            "timeout"
            in EnumDispatchStatus.get_description(EnumDispatchStatus.TIMEOUT).lower()
        )
        assert (
            "validation"
            in EnumDispatchStatus.get_description(
                EnumDispatchStatus.INVALID_MESSAGE
            ).lower()
        )

        # All statuses should have non-empty descriptions
        for status in EnumDispatchStatus:
            description = EnumDispatchStatus.get_description(status)
            assert description is not None
            assert len(description) > 0

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumDispatchStatus.SUCCESS == EnumDispatchStatus.SUCCESS
        assert EnumDispatchStatus.SUCCESS != EnumDispatchStatus.HANDLER_ERROR
        assert EnumDispatchStatus.TIMEOUT == EnumDispatchStatus.TIMEOUT

    def test_enum_membership(self):
        """Test enum membership checking."""
        for status in EnumDispatchStatus:
            assert status in EnumDispatchStatus

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        status = EnumDispatchStatus.HANDLER_ERROR
        json_str = json.dumps(status, default=str)
        assert json_str == '"handler_error"'

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class DispatchModel(BaseModel):
            status: EnumDispatchStatus

        # Test valid enum assignment
        model = DispatchModel(status=EnumDispatchStatus.SUCCESS)
        assert model.status == EnumDispatchStatus.SUCCESS

        # Test string assignment
        model = DispatchModel(status="timeout")
        assert model.status == EnumDispatchStatus.TIMEOUT

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            DispatchModel(status="invalid_status")

    def test_status_consistency(self):
        """Test logical consistency of status categorization."""
        for status in EnumDispatchStatus:
            is_terminal = status.is_terminal()
            is_successful = status.is_successful()
            is_error = status.is_error()
            requires_retry = status.requires_retry()

            # If successful, should be terminal
            if is_successful:
                assert is_terminal, f"{status} is successful but not terminal"

            # If requires retry, should be an error
            if requires_retry:
                assert is_error, f"{status} requires retry but is not an error"

            # SUCCESS should not be an error
            if status == EnumDispatchStatus.SUCCESS:
                assert not is_error
                assert not requires_retry

    def test_terminal_and_error_relationship(self):
        """Test relationship between terminal and error states."""
        # All error states should be terminal
        for status in EnumDispatchStatus:
            if status.is_error():
                assert status.is_terminal(), f"{status} is error but not terminal"

        # But not all terminal states are errors (SUCCESS and SKIPPED)
        assert EnumDispatchStatus.SUCCESS.is_terminal()
        assert not EnumDispatchStatus.SUCCESS.is_error()

        assert EnumDispatchStatus.SKIPPED.is_terminal()
        assert not EnumDispatchStatus.SKIPPED.is_error()

    def test_routed_is_intermediate_state(self):
        """Test that ROUTED is the only intermediate (non-terminal) state."""
        intermediate_states = [s for s in EnumDispatchStatus if not s.is_terminal()]
        assert len(intermediate_states) == 1
        assert EnumDispatchStatus.ROUTED in intermediate_states

        # ROUTED should not be successful, error, or require retry
        assert not EnumDispatchStatus.ROUTED.is_successful()
        assert not EnumDispatchStatus.ROUTED.is_error()
        assert not EnumDispatchStatus.ROUTED.requires_retry()

    def test_all_statuses_have_description(self):
        """Test that all statuses have meaningful descriptions."""
        for status in EnumDispatchStatus:
            description = EnumDispatchStatus.get_description(status)
            assert description != "Unknown dispatch status"
            assert len(description) > 10  # Meaningful description

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        data = {"status": EnumDispatchStatus.TIMEOUT.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "status: timeout" in yaml_str

        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["status"] == "timeout"

    def test_roundtrip_serialization_all_values(self):
        """Test roundtrip serialization for all enum values.

        Ensures str(enum) -> Enum(str) works for every value.
        """
        for status in EnumDispatchStatus:
            # String roundtrip
            serialized = str(status)
            deserialized = EnumDispatchStatus(serialized)
            assert deserialized == status, (
                f"String roundtrip failed for {status}: "
                f"serialized={serialized}, deserialized={deserialized}"
            )

            # Value roundtrip
            value = status.value
            reconstructed = EnumDispatchStatus(value)
            assert reconstructed == status, (
                f"Value roundtrip failed for {status}: "
                f"value={value}, reconstructed={reconstructed}"
            )

    def test_is_terminal_exhaustive(self):
        """Test is_terminal returns correct values for ALL statuses.

        Exhaustive test to ensure all 8 statuses are covered.
        """
        terminal_statuses = {
            EnumDispatchStatus.SUCCESS,
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
            EnumDispatchStatus.SKIPPED,
        }

        for status in EnumDispatchStatus:
            expected = status in terminal_statuses
            assert status.is_terminal() == expected, (
                f"is_terminal() mismatch for {status}: "
                f"expected={expected}, actual={status.is_terminal()}"
            )

    def test_is_terminal_completeness(self):
        """Test that all status values are categorized by is_terminal.

        Every status must be either terminal or non-terminal.
        This ensures no status values are left uncategorized.
        """
        terminal_count = sum(1 for s in EnumDispatchStatus if s.is_terminal())
        non_terminal_count = len(EnumDispatchStatus) - terminal_count

        # All statuses should be accounted for
        assert terminal_count + non_terminal_count == len(EnumDispatchStatus)

        # Expected counts based on the enum definition
        assert terminal_count == 7  # All except ROUTED
        assert non_terminal_count == 1  # Only ROUTED

    def test_is_successful_exhaustive(self):
        """Test is_successful returns correct values for ALL statuses.

        Exhaustive test to ensure all 8 statuses are covered.
        """
        for status in EnumDispatchStatus:
            expected = status == EnumDispatchStatus.SUCCESS
            assert status.is_successful() == expected, (
                f"is_successful() mismatch for {status}: "
                f"expected={expected}, actual={status.is_successful()}"
            )

    def test_is_error_exhaustive(self):
        """Test is_error returns correct values for ALL statuses.

        Exhaustive test to ensure all 8 statuses are covered.
        """
        error_statuses = {
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
        }

        for status in EnumDispatchStatus:
            expected = status in error_statuses
            assert status.is_error() == expected, (
                f"is_error() mismatch for {status}: "
                f"expected={expected}, actual={status.is_error()}"
            )

    def test_requires_retry_exhaustive(self):
        """Test requires_retry returns correct values for ALL statuses.

        Exhaustive test to ensure all 8 statuses are covered.
        """
        retry_statuses = {
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.PUBLISH_FAILED,
        }

        for status in EnumDispatchStatus:
            expected = status in retry_statuses
            assert status.requires_retry() == expected, (
                f"requires_retry() mismatch for {status}: "
                f"expected={expected}, actual={status.requires_retry()}"
            )
