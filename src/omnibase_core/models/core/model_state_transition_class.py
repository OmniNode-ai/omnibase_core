"""
State Transition Model.

Model for state transitions in contract-driven state management.

This model represents state transitions that can be defined in contracts
to specify how state should change in response to actions.
"""

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_transition_type import EnumTransitionType
from omnibase_core.models.core.model_conditional_transition import (
    ModelConditionalTransition,
)
from omnibase_core.models.core.model_simple_transition import ModelSimpleTransition
from omnibase_core.models.core.model_state_transition_condition import (
    ModelStateTransitionCondition,
)
from omnibase_core.models.core.model_tool_based_transition import (
    ModelToolBasedTransition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelStateTransition(BaseModel):
    """
    Represents a state transition that can be defined in a contract.

    State transitions define how the node's state should change in response
    to specific actions or events.
    """

    # Transition identification
    name: str = Field(default=..., description="Unique name for this transition")

    description: str | None = Field(
        default=None,
        description="Human-readable description of what this transition does",
    )

    # Trigger configuration
    triggers: list[str] = Field(
        default=...,
        description="Action types or events that trigger this transition",
    )

    priority: int = Field(
        default=0,
        description="Priority when multiple transitions match (higher = earlier)",
    )

    # Transition type and configuration
    transition_type: EnumTransitionType = Field(
        default=..., description="Type of transition"
    )

    # Type-specific configuration (only one should be set)
    simple_config: ModelSimpleTransition | None = Field(
        default=None,
        description="Configuration for simple transitions",
    )

    tool_config: ModelToolBasedTransition | None = Field(
        default=None,
        description="Configuration for tool-based transitions",
    )

    conditional_config: ModelConditionalTransition | None = Field(
        default=None,
        description="Configuration for conditional transitions",
    )

    composite_config: list["ModelStateTransition"] | None = Field(
        default=None,
        description="Sub-transitions for composite transitions",
    )

    # Pre/post conditions
    preconditions: list[ModelStateTransitionCondition] | None = Field(
        default=None,
        description="Conditions that must be met before transition",
    )

    postconditions: list[ModelStateTransitionCondition] | None = Field(
        default=None,
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
        default=None,
        description="Event types to emit after successful transition",
    )

    # Error handling
    on_error: str | None = Field(
        default="fail",
        description="Error handling strategy: 'fail', 'skip', 'rollback', 'retry'",
    )

    max_retries: int | None = Field(
        default=0,
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
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
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
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        return self

    @classmethod
    def create_simple(
        cls,
        name: str,
        triggers: list[str],
        updates: SerializedDict,
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
        tool_params: SerializedDict | None = None,
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


# Enable forward reference resolution
ModelStateTransition.model_rebuild()
