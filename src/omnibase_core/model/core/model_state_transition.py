"""
Model for state transitions in contract-driven state management.

This model represents state transitions that can be defined in contracts
to specify how state should change in response to actions.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class EnumTransitionType(str, Enum):
    """Types of state transitions."""

    SIMPLE = "simple"  # Direct field updates
    TOOL_BASED = "tool_based"  # Delegate to tool for computation
    CONDITIONAL = "conditional"  # Apply based on conditions
    COMPOSITE = "composite"  # Combine multiple transitions


class ModelStateTransitionCondition(BaseModel):
    """Condition that must be met for a transition to apply."""

    expression: str = Field(
        ..., description="Expression to evaluate (e.g., 'state.count > 10')"
    )

    error_message: Optional[str] = Field(
        None, description="Error message if condition fails"
    )

    required_fields: Optional[List[str]] = Field(
        None, description="Fields that must exist in state for condition"
    )


class ModelSimpleTransition(BaseModel):
    """Simple direct state field updates."""

    updates: Dict[str, Any] = Field(
        ..., description="Field path to value mappings (e.g., {'user.name': 'John'})"
    )

    merge_strategy: Optional[str] = Field(
        "replace",
        description="How to handle existing values: 'replace', 'merge', 'append'",
    )


class ModelToolBasedTransition(BaseModel):
    """Transition that delegates to a tool for state computation."""

    tool_name: str = Field(
        ..., description="Name of the tool to invoke (e.g., 'tool_state_calculator')"
    )

    tool_params: Optional[Dict[str, Any]] = Field(
        None, description="Additional parameters to pass to the tool"
    )

    fallback_updates: Optional[Dict[str, Any]] = Field(
        None, description="Updates to apply if tool invocation fails"
    )

    timeout_ms: Optional[int] = Field(
        5000, description="Tool invocation timeout in milliseconds"
    )


class ModelConditionalTransition(BaseModel):
    """Transition that applies different updates based on conditions."""

    branches: List[Dict[str, Any]] = Field(
        ..., description="List of condition/transition pairs"
    )

    default_transition: Optional[Dict[str, Any]] = Field(
        None, description="Transition to apply if no conditions match"
    )


class ModelStateTransition(BaseModel):
    """
    Represents a state transition that can be defined in a contract.

    State transitions define how the node's state should change in response
    to specific actions or events.
    """

    # Transition identification
    name: str = Field(..., description="Unique name for this transition")

    description: Optional[str] = Field(
        None, description="Human-readable description of what this transition does"
    )

    # Trigger configuration
    triggers: List[str] = Field(
        ..., description="Action types or events that trigger this transition"
    )

    priority: int = Field(
        default=0,
        description="Priority when multiple transitions match (higher = earlier)",
    )

    # Transition type and configuration
    transition_type: EnumTransitionType = Field(..., description="Type of transition")

    # Type-specific configuration (only one should be set)
    simple_config: Optional[ModelSimpleTransition] = Field(
        None, description="Configuration for simple transitions"
    )

    tool_config: Optional[ModelToolBasedTransition] = Field(
        None, description="Configuration for tool-based transitions"
    )

    conditional_config: Optional[ModelConditionalTransition] = Field(
        None, description="Configuration for conditional transitions"
    )

    composite_config: Optional[List["ModelStateTransition"]] = Field(
        None, description="Sub-transitions for composite transitions"
    )

    # Pre/post conditions
    preconditions: Optional[List[ModelStateTransitionCondition]] = Field(
        None, description="Conditions that must be met before transition"
    )

    postconditions: Optional[List[ModelStateTransitionCondition]] = Field(
        None, description="Conditions that must be met after transition"
    )

    # Validation and side effects
    validate_before: bool = Field(
        default=True, description="Whether to validate state before transition"
    )

    validate_after: bool = Field(
        default=True, description="Whether to validate state after transition"
    )

    emit_events: Optional[List[str]] = Field(
        None, description="Event types to emit after successful transition"
    )

    # Error handling
    on_error: Optional[str] = Field(
        "fail",
        description="Error handling strategy: 'fail', 'skip', 'rollback', 'retry'",
    )

    max_retries: Optional[int] = Field(
        0, description="Maximum retry attempts for failed transitions"
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
                raise ValueError(
                    f"{expected_field} is required for {self.transition_type} transitions"
                )

        # Check that other configs are not set
        for field_name, config_value in [
            ("simple_config", self.simple_config),
            ("tool_config", self.tool_config),
            ("conditional_config", self.conditional_config),
            ("composite_config", self.composite_config),
        ]:
            if field_name != expected_field and config_value is not None:
                raise ValueError(
                    f"{field_name} should not be set for {self.transition_type} transitions"
                )

        return self

    @classmethod
    def create_simple(
        cls,
        name: str,
        triggers: List[str],
        updates: Dict[str, Any],
        description: Optional[str] = None,
    ) -> "ModelStateTransition":
        """Factory method for simple transitions."""
        return cls(
            name=name,
            description=description,
            triggers=triggers,
            transition_type=EnumTransitionType.SIMPLE,
            simple_config=ModelSimpleTransition(updates=updates),
        )

    @classmethod
    def create_tool_based(
        cls,
        name: str,
        triggers: List[str],
        tool_name: str,
        tool_params: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> "ModelStateTransition":
        """Factory method for tool-based transitions."""
        return cls(
            name=name,
            description=description,
            triggers=triggers,
            transition_type=EnumTransitionType.TOOL_BASED,
            tool_config=ModelToolBasedTransition(
                tool_name=tool_name, tool_params=tool_params
            ),
        )


# Enable forward reference resolution
ModelStateTransition.model_rebuild()
