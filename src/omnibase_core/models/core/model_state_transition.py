"""
Model for state transitions in contract-driven state management.

This model represents state transitions that can be defined in contracts
to specify how state should change in response to actions.
"""

from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, model_validator

from .model_state_transition_types import (
    ModelConditionalBranch,
    ModelDefaultTransition,
    ModelStateUpdate,
    ModelToolParameter,
)


class EnumTransitionType(str, Enum):
    """Types of state transitions."""

    SIMPLE = "simple"  # Direct field updates
    TOOL_BASED = "tool_based"  # Delegate to tool for computation
    CONDITIONAL = "conditional"  # Apply based on conditions
    COMPOSITE = "composite"  # Combine multiple transitions


class ModelStateTransitionCondition(BaseModel):
    """Condition that must be met for a transition to apply."""

    expression: str = Field(
        ...,
        description="Expression to evaluate (e.g., 'state.count > 10')",
    )

    error_message: str | None = Field(
        None,
        description="Error message if condition fails",
    )

    required_fields: list[str] | None = Field(
        None,
        description="Fields that must exist in state for condition",
    )


class ModelSimpleTransition(BaseModel):
    """Simple direct state field updates."""

    updates: list[ModelStateUpdate] = Field(
        ...,
        description="List of state updates to apply",
    )

    merge_strategy: str | None = Field(
        "replace",
        description="How to handle existing values: 'replace', 'merge', 'append'",
    )


class ModelToolBasedTransition(BaseModel):
    """Transition that delegates to a tool for state computation."""

    tool_name: str = Field(
        ...,
        description="Name of the tool to invoke (e.g., 'tool_state_calculator')",
    )

    tool_params: list[ModelToolParameter] | None = Field(
        None,
        description="Parameters to pass to the tool",
    )

    fallback_updates: list[ModelStateUpdate] | None = Field(
        None,
        description="Updates to apply if tool invocation fails",
    )

    timeout_ms: int | None = Field(
        5000,
        description="Tool invocation timeout in milliseconds",
    )


class ModelConditionalTransition(BaseModel):
    """Transition that applies different updates based on conditions."""

    branches: list[ModelConditionalBranch] = Field(
        ...,
        description="List of conditional branches",
    )

    default_transition: ModelDefaultTransition | None = Field(
        None,
        description="Transition to apply if no conditions match",
    )


class ModelStateTransition(BaseModel):
    """
    Represents a state transition that can be defined in a contract.

    State transitions define how the node's state should change in response
    to specific actions or events.
    """

    # Transition identification
    name: str = Field(..., description="Unique name for this transition")

    description: str | None = Field(
        None,
        description="Human-readable description of what this transition does",
    )

    # Trigger configuration
    triggers: list[str] = Field(
        ...,
        description="Action types or events that trigger this transition",
    )

    priority: int = Field(
        default=0,
        description="Priority when multiple transitions match (higher = earlier)",
    )

    # Transition type and configuration
    transition_type: EnumTransitionType = Field(..., description="Type of transition")

    # Type-specific configuration (only one should be set)
    simple_config: ModelSimpleTransition | None = Field(
        None,
        description="Configuration for simple transitions",
    )

    tool_config: ModelToolBasedTransition | None = Field(
        None,
        description="Configuration for tool-based transitions",
    )

    conditional_config: ModelConditionalTransition | None = Field(
        None,
        description="Configuration for conditional transitions",
    )

    composite_config: list["ModelStateTransition"] | None = Field(
        None,
        description="Sub-transitions for composite transitions",
    )

    # Pre/post conditions
    preconditions: list[ModelStateTransitionCondition] | None = Field(
        None,
        description="Conditions that must be met before transition",
    )

    postconditions: list[ModelStateTransitionCondition] | None = Field(
        None,
        description="Conditions that must be met after transition",
    )

    # Validation and side effects
    validate_before: bool = Field(
        default=True,
        description="Whether to validate state before transition",
    )

    validate_after: bool = Field(
        default=True,
        description="Whether to validate state after transition",
    )

    emit_events: list[str] | None = Field(
        None,
        description="Event types to emit after successful transition",
    )

    # Error handling
    on_error: str | None = Field(
        "fail",
        description="Error handling strategy: 'fail', 'skip', 'rollback', 'retry'",
    )

    max_retries: int | None = Field(
        0,
        description="Maximum retry attempts for failed transitions",
    )

    @model_validator(mode="after")
    def validate_transition_config(self) -> "ModelStateTransition":
        """Ensure only one transition config type is set."""
        # Map transition types to their config fields
        type_to_field = {
            EnumTransitionType.SIMPLE: "simple_config",
            EnumTransitionType.TOOL_BASED: "tool_config",
            EnumTransitionType.CONDITIONAL: "conditional_config",
            EnumTransitionType.COMPOSITE: "composite_config",
        }

        expected_field = type_to_field.get(self.transition_type)

        # Check that the required config is set
        if expected_field:
            expected_value = getattr(self, expected_field)
            if expected_value is None:
                msg = f"{expected_field} is required for {self.transition_type} transitions"
                raise ValueError(
                    msg,
                )

        # Check that other configs are not set
        for field_name, config_value in [
            ("simple_config", self.simple_config),
            ("tool_config", self.tool_config),
            ("conditional_config", self.conditional_config),
            ("composite_config", self.composite_config),
        ]:
            if field_name != expected_field and config_value is not None:
                msg = f"{field_name} should not be set for {self.transition_type} transitions"
                raise ValueError(
                    msg,
                )

        return self

    @classmethod
    def create_simple(
        cls,
        name: str,
        triggers: list[str],
        updates: Union[
            dict[str, Union[str, int, float, bool, None]], list[ModelStateUpdate]
        ],
        description: str | None = None,
    ) -> "ModelStateTransition":
        """Factory method for simple transitions."""
        # Convert dict updates to ModelStateUpdate objects
        update_objects = (
            [
                ModelStateUpdate(field_path=key, value=value)
                for key, value in updates.items()
                if isinstance(updates, dict)
            ]
            if isinstance(updates, dict)
            else updates
        )

        return cls(
            name=name,
            description=description,
            triggers=triggers,
            transition_type=EnumTransitionType.SIMPLE,
            simple_config=ModelSimpleTransition(
                updates=update_objects, merge_strategy="replace"
            ),
            tool_config=None,
            conditional_config=None,
            composite_config=None,
            preconditions=None,
            postconditions=None,
            emit_events=None,
            on_error="fail",
            max_retries=0,
        )

    @classmethod
    def create_tool_based(
        cls,
        name: str,
        triggers: list[str],
        tool_name: str,
        tool_params: Union[
            dict[str, Union[str, int, float, bool, None]],
            list[ModelToolParameter],
            None,
        ] = None,
        description: str | None = None,
    ) -> "ModelStateTransition":
        """Factory method for tool-based transitions."""
        # Convert dict tool_params to ModelToolParameter objects
        param_objects = None
        if tool_params:
            if isinstance(tool_params, dict):
                param_objects = [
                    ModelToolParameter(name=key, value=value)
                    for key, value in tool_params.items()
                ]
            else:
                param_objects = tool_params

        return cls(
            name=name,
            description=description,
            triggers=triggers,
            transition_type=EnumTransitionType.TOOL_BASED,
            simple_config=None,
            tool_config=ModelToolBasedTransition(
                tool_name=tool_name,
                tool_params=param_objects,
                fallback_updates=None,
                timeout_ms=5000,
            ),
            conditional_config=None,
            composite_config=None,
            preconditions=None,
            postconditions=None,
            emit_events=None,
            on_error="fail",
            max_retries=0,
        )


# Enable forward reference resolution
ModelStateTransition.model_rebuild()
