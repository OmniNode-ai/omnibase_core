# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelFSMTransitionAction.

Validates FSM transition action configuration including
uniqueness constraints on parameter names.
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.contracts.model_action_config_parameter import (
    ModelActionConfigParameter,
)
from omnibase_core.models.contracts.subcontracts.model_fsmtransitionaction import (
    ModelFSMTransitionAction,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelFSMTransitionActionValidation:
    """Test validation rules for FSM transition actions."""

    def test_valid_action_with_unique_parameters(self) -> None:
        """Test that actions with unique parameter names are valid."""
        action = ModelFSMTransitionAction(
            version=DEFAULT_VERSION,
            action_name="log_transition",
            action_type="log",
            action_config=[
                ModelActionConfigParameter(
                    name="level",
                    type="string",
                    required=True,
                    default="info",
                ),
                ModelActionConfigParameter(
                    name="message",
                    type="string",
                    required=True,
                    default="State transition occurred",
                ),
            ],
        )
        assert action.action_name == "log_transition"
        assert len(action.action_config) == 2

    def test_invalid_action_with_duplicate_parameters(self) -> None:
        """Test that actions with duplicate parameter names raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelFSMTransitionAction(
                version=DEFAULT_VERSION,
                action_name="invalid_action",
                action_type="validate",
                action_config=[
                    ModelActionConfigParameter(
                        name="threshold",
                        type="int",
                        required=True,
                        default=100,
                    ),
                    ModelActionConfigParameter(
                        name="threshold",  # Duplicate!
                        type="int",
                        required=True,
                        default=200,
                    ),
                ],
            )

        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert "threshold" in error_msg
        assert "Duplicate parameter names" in error_msg

    def test_invalid_action_with_multiple_duplicates(self) -> None:
        """Test that multiple duplicate parameter names are all reported."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelFSMTransitionAction(
                version=DEFAULT_VERSION,
                action_name="invalid_action",
                action_type="validate",
                action_config=[
                    ModelActionConfigParameter(
                        name="param_a",
                        type="string",
                        required=True,
                        default="value1",
                    ),
                    ModelActionConfigParameter(
                        name="param_a",  # Duplicate!
                        type="string",
                        required=True,
                        default="value2",
                    ),
                    ModelActionConfigParameter(
                        name="param_b",
                        type="string",
                        required=True,
                        default="value3",
                    ),
                    ModelActionConfigParameter(
                        name="param_b",  # Duplicate!
                        type="string",
                        required=True,
                        default="value4",
                    ),
                ],
            )

        error_msg = str(exc_info.value)
        assert "param_a" in error_msg
        assert "param_b" in error_msg

    def test_valid_action_with_empty_config(self) -> None:
        """Test that actions with empty config are valid."""
        action = ModelFSMTransitionAction(
            version=DEFAULT_VERSION,
            action_name="simple_action",
            action_type="event",
            action_config=[],  # Empty is valid
        )
        assert action.action_name == "simple_action"
        assert len(action.action_config) == 0

    def test_valid_action_with_single_parameter(self) -> None:
        """Test that actions with a single parameter are valid."""
        action = ModelFSMTransitionAction(
            version=DEFAULT_VERSION,
            action_name="single_param_action",
            action_type="modify",
            action_config=[
                ModelActionConfigParameter(
                    name="target",
                    type="string",
                    required=True,
                    default="state_field",
                ),
            ],
        )
        assert action.action_name == "single_param_action"
        assert len(action.action_config) == 1


@pytest.mark.unit
class TestModelFSMTransitionActionCreation:
    """Test creation and field constraints."""

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionAction(version=DEFAULT_VERSION)  # type: ignore[call-arg]

    def test_default_values(self) -> None:
        """Test default field values."""
        action = ModelFSMTransitionAction(
            version=DEFAULT_VERSION,
            action_name="test_action",
            action_type="log",
        )
        assert action.execution_order == 1
        assert action.is_critical is False
        assert action.rollback_action is None
        assert action.timeout_ms is None
        assert action.action_config == []  # Default is empty list

    def test_optional_fields(self) -> None:
        """Test optional field assignment."""
        action = ModelFSMTransitionAction(
            version=DEFAULT_VERSION,
            action_name="test_action",
            action_type="log",
            execution_order=5,
            is_critical=True,
            rollback_action="rollback_log",
            timeout_ms=5000,
        )
        assert action.execution_order == 5
        assert action.is_critical is True
        assert action.rollback_action == "rollback_log"
        assert action.timeout_ms == 5000

    def test_string_field_constraints(self) -> None:
        """Test string field minimum length constraints."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionAction(
                version=DEFAULT_VERSION,
                action_name="",  # Empty string not allowed
                action_type="log",
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionAction(
                version=DEFAULT_VERSION,
                action_name="test",
                action_type="",  # Empty string not allowed
            )

    def test_numeric_field_constraints(self) -> None:
        """Test numeric field constraints."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionAction(
                version=DEFAULT_VERSION,
                action_name="test",
                action_type="log",
                execution_order=0,  # Must be >= 1
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionAction(
                version=DEFAULT_VERSION,
                action_name="test",
                action_type="log",
                timeout_ms=0,  # Must be >= 1
            )
