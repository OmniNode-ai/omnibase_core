# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelFSMStateDefinition.

Validates FSM state definition configuration including:
- Immutability (frozen=True) enforcement
- Terminal state and recoverable state validation logic
- Required field enforcement
- Field constraints and default values
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field
DEFAULT_VERSION = ModelSemVer(major=1, minor=5, patch=0)


@pytest.mark.unit
class TestModelFSMStateDefinitionImmutability:
    """Test frozen model configuration for immutability."""

    def test_is_frozen(self) -> None:
        """Test that ModelFSMStateDefinition is immutable after creation.

        The model uses frozen=True in ConfigDict, which makes instances
        immutable. Any attempt to modify a field after creation should
        raise a ValidationError.
        """
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="test_state",
            state_type="operational",
            description="Test state for immutability verification",
        )

        # Verify the instance was created successfully
        assert state.state_name == "test_state"

        # Attempt to modify a field should raise ValidationError
        with pytest.raises(ValidationError):
            state.state_name = "modified_name"  # type: ignore[misc]

    def test_is_frozen_all_fields(self) -> None:
        """Test that all fields are immutable after creation."""
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="test_state",
            state_type="operational",
            description="Test state",
            is_terminal=False,
            is_recoverable=True,
        )

        # Attempt to modify various fields should all raise ValidationError
        with pytest.raises(ValidationError):
            state.state_type = "error"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            state.description = "Modified description"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            state.is_terminal = True  # type: ignore[misc]

        with pytest.raises(ValidationError):
            state.is_recoverable = False  # type: ignore[misc]


@pytest.mark.unit
class TestModelFSMStateDefinitionTerminalRecoverableValidation:
    """Test validation rules for terminal and recoverable state combinations."""

    def test_terminal_state_cannot_be_recoverable(self) -> None:
        """Test that terminal states cannot have is_recoverable=True.

        This is a logical contradiction: terminal states represent completed
        workflows that cannot be re-entered, so recovery is not possible.
        The validator should raise ModelOnexError with VALIDATION_ERROR code.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="completed_state",
                state_type="terminal",
                description="A terminal state that should not be recoverable",
                is_terminal=True,
                is_recoverable=True,  # Invalid combination
            )

        # Verify the error code
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        # Verify the error message contains relevant information
        assert "completed_state" in exc_info.value.message
        assert (
            "is_recoverable" in exc_info.value.message
            or "recoverable" in exc_info.value.message.lower()
        )

    def test_terminal_state_with_recoverable_false_allowed(self) -> None:
        """Test that terminal states with is_recoverable=False are valid.

        This is the correct combination: terminal states should have
        is_recoverable=False since they cannot be re-entered.
        """
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="final_state",
            state_type="terminal",
            description="A valid terminal state",
            is_terminal=True,
            is_recoverable=False,
        )

        # Verify the state was created successfully
        assert state.state_name == "final_state"
        assert state.is_terminal is True
        assert state.is_recoverable is False

    def test_non_terminal_state_can_be_recoverable(self) -> None:
        """Test that non-terminal states can have is_recoverable=True.

        Non-terminal states represent intermediate workflow steps that
        can be recovered from if an error occurs.
        """
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="processing_state",
            state_type="operational",
            description="An operational state that can be recovered",
            is_terminal=False,
            is_recoverable=True,
        )

        # Verify the state was created successfully
        assert state.state_name == "processing_state"
        assert state.is_terminal is False
        assert state.is_recoverable is True

    def test_non_terminal_state_can_be_non_recoverable(self) -> None:
        """Test that non-terminal states can also have is_recoverable=False.

        Some intermediate states may not support recovery even though
        they are not terminal states.
        """
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="critical_state",
            state_type="operational",
            description="An operational state that cannot be recovered",
            is_terminal=False,
            is_recoverable=False,
        )

        # Verify the state was created successfully
        assert state.state_name == "critical_state"
        assert state.is_terminal is False
        assert state.is_recoverable is False


@pytest.mark.unit
class TestModelFSMStateDefinitionRequiredFields:
    """Test required field validation."""

    def test_required_fields_validation(self) -> None:
        """Test that required fields (version, state_name, state_type, description) are enforced."""
        # Missing version
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                state_name="test_state",
                state_type="operational",
                description="Test state",
            )  # type: ignore[call-arg]

        # Missing state_name
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_type="operational",
                description="Test state",
            )  # type: ignore[call-arg]

        # Missing state_type
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                description="Test state",
            )  # type: ignore[call-arg]

        # Missing description
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                state_type="operational",
            )  # type: ignore[call-arg]

    def test_all_required_fields_missing(self) -> None:
        """Test that creating instance with no arguments raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition()  # type: ignore[call-arg]

    def test_empty_string_fields_not_allowed(self) -> None:
        """Test that empty strings are not allowed for required string fields."""
        # Empty state_name
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="",  # Empty string not allowed (min_length=1)
                state_type="operational",
                description="Test state",
            )

        # Empty state_type
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                state_type="",  # Empty string not allowed (min_length=1)
                description="Test state",
            )

        # Empty description
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                state_type="operational",
                description="",  # Empty string not allowed (min_length=1)
            )


@pytest.mark.unit
class TestModelFSMStateDefinitionDefaultValues:
    """Test default field values."""

    def test_default_values(self) -> None:
        """Test that optional fields have correct default values."""
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="test_state",
            state_type="operational",
            description="Test state",
        )

        # Check default values
        assert state.is_terminal is False
        assert state.is_recoverable is True
        assert state.timeout_ms is None
        assert state.entry_actions == []
        assert state.exit_actions == []
        assert state.required_data == []
        assert state.optional_data == []
        assert state.validation_rules == []


@pytest.mark.unit
class TestModelFSMStateDefinitionOptionalFields:
    """Test optional field assignment."""

    def test_optional_fields_assignment(self) -> None:
        """Test that optional fields can be assigned values."""
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="comprehensive_state",
            state_type="operational",
            description="State with all optional fields",
            is_terminal=False,
            is_recoverable=True,
            timeout_ms=5000,
            entry_actions=["log_entry", "notify_start"],
            exit_actions=["log_exit", "cleanup"],
            required_data=["user_id", "session_id"],
            optional_data=["metadata", "tags"],
            validation_rules=["validate_user", "validate_session"],
        )

        assert state.timeout_ms == 5000
        assert state.entry_actions == ["log_entry", "notify_start"]
        assert state.exit_actions == ["log_exit", "cleanup"]
        assert state.required_data == ["user_id", "session_id"]
        assert state.optional_data == ["metadata", "tags"]
        assert state.validation_rules == ["validate_user", "validate_session"]

    def test_timeout_ms_validation(self) -> None:
        """Test that timeout_ms must be >= 1 if provided."""
        # Valid timeout
        state = ModelFSMStateDefinition(
            version=DEFAULT_VERSION,
            state_name="test_state",
            state_type="operational",
            description="Test state",
            timeout_ms=1,  # Minimum valid value
        )
        assert state.timeout_ms == 1

        # Invalid timeout (0)
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                state_type="operational",
                description="Test state",
                timeout_ms=0,  # Below minimum
            )

        # Invalid timeout (negative)
        with pytest.raises(ValidationError):
            ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                state_type="operational",
                description="Test state",
                timeout_ms=-1,  # Negative not allowed
            )


@pytest.mark.unit
class TestModelFSMStateDefinitionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_state_name_with_special_characters(self) -> None:
        """Test that state names with special characters are valid."""
        special_names = [
            "state_with_underscore",
            "state-with-dash",
            "state.with.dot",
            "state123",
            "STATE_UPPER",
        ]
        for name in special_names:
            state = ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name=name,
                state_type="operational",
                description="Test state",
            )
            assert state.state_name == name

    def test_state_type_variations(self) -> None:
        """Test different state_type values are accepted."""
        state_types = ["operational", "snapshot", "error", "terminal", "custom_type"]
        for state_type in state_types:
            state = ModelFSMStateDefinition(
                version=DEFAULT_VERSION,
                state_name="test_state",
                state_type=state_type,
                description="Test state",
            )
            assert state.state_type == state_type

    def test_version_tracking(self) -> None:
        """Test that version is correctly stored and accessible."""
        custom_version = ModelSemVer(major=2, minor=0, patch=1)
        state = ModelFSMStateDefinition(
            version=custom_version,
            state_name="versioned_state",
            state_type="operational",
            description="State with custom version",
        )
        assert state.version.major == 2
        assert state.version.minor == 0
        assert state.version.patch == 1
