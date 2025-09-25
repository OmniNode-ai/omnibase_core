"""
Model for state transitions in contract-driven state management.

This model represents state transitions that can be defined in contracts
to specify how state should change in response to actions.
"""

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

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

    updates: dict[str, Any] = Field(
        ...,
        description="Field path to value mappings (e.g., {'user.name': 'John'})",
    )

    merge_strategy: str | None = Field(
        "replace",
        description="How to handle existing values: 'replace', 'merge', 'append'",
    )


class ModelToolBasedTransition(BaseModel):
    """Transition that delegates to a tool for state computation."""

    tool_id: UUID = Field(
        ...,
        description="UUID of the tool to invoke",
    )

    tool_display_name: str | None = Field(
        None,
        description="Human-readable name of the tool (e.g., 'State Calculator Tool')",
    )

    tool_params: dict[str, Any] | None = Field(
        None,
        description="Additional parameters to pass to the tool",
    )

    fallback_updates: dict[str, Any] | None = Field(
        None,
        description="Updates to apply if tool invocation fails",
    )

    timeout_ms: int | None = Field(
        5000,
        description="Tool invocation timeout in milliseconds",
    )

    @property
    def tool_name(self) -> str:
        """Backward compatibility property for tool_name."""
        return self.tool_display_name or f"tool_{str(self.tool_id)[:8]}"

    @tool_name.setter
    def tool_name(self, value: str) -> None:
        """Backward compatibility setter for tool_name."""
        self.tool_display_name = value


class ModelConditionalTransition(BaseModel):
    """Transition that applies different updates based on conditions."""

    branches: list[dict[str, Any]] = Field(
        ...,
        description="List of condition/transition pairs",
    )

    default_transition: dict[str, Any] | None = Field(
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
        updates: dict[str, Any],
        description: str | None = None,
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
        triggers: list[str],
        tool_id: UUID,
        tool_display_name: str | None = None,
        tool_params: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> "ModelStateTransition":
        """Factory method for tool-based transitions."""
        return cls(
            name=name,
            description=description,
            triggers=triggers,
            transition_type=EnumTransitionType.TOOL_BASED,
            tool_config=ModelToolBasedTransition(
                tool_id=tool_id,
                tool_display_name=tool_display_name,
                tool_params=tool_params,
            ),
        )

    @classmethod
    def create_tool_based_legacy(
        cls,
        name: str,
        triggers: list[str],
        tool_name: str,
        tool_params: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> "ModelStateTransition":
        """Legacy factory method for tool-based transitions using tool name."""
        # Generate a UUID from the tool name for backward compatibility
        import hashlib

        name_hash = hashlib.sha256(tool_name.encode()).hexdigest()
        tool_id = UUID(
            f"{name_hash[:8]}-{name_hash[8:12]}-{name_hash[12:16]}-{name_hash[16:20]}-{name_hash[20:32]}"
        )

        return cls.create_tool_based(
            name=name,
            triggers=triggers,
            tool_id=tool_id,
            tool_display_name=tool_name,
            tool_params=tool_params,
            description=description,
        )


# Enable forward reference resolution
ModelStateTransition.model_rebuild()
