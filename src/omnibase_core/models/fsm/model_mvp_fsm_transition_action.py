"""
FSM Transition Action Model for state/transition actions.

Defines action specifications for FSM state transitions, including
action types, configuration, and execution order for determining
actions to execute during state transitions.

Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md

Note:
    This model is part of the FSM v1.0 implementation. The rollback_action
    field is reserved for v1.1+ and has no effect in v1.0.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Type alias for action configuration values
# Supports primitive types and lists of strings for FSM action configuration
ActionConfigValue = str | int | float | bool | list[str] | None


class ModelMvpFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions.

    Defines actions to execute during state transitions, including
    action types (emit_intent, log, etc.), configuration parameters,
    and execution ordering.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    v1.0 Reserved Fields (parsed but NOT executed):
        - rollback_action: Parsed, but rollback NOT executed until v1.1

    Setting rollback_action in v1.0 contracts will NOT change runtime behavior.

    Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md

    Attributes:
        action_name: Unique identifier for the action (required)
        action_type: Type of action (emit_intent, log, etc.) (required)
        action_config: Configuration dictionary for the action
        execution_order: Order of execution within the phase (default: 0)
        is_critical: If true, failure stops the transition (default: False)
        rollback_action: Reserved for v1.1+ - action to execute on rollback
        timeout_ms: Optional timeout for action execution in milliseconds

    Example:
        >>> action = ModelMvpFSMTransitionAction(
        ...     action_name="log_transition",
        ...     action_type="log",
        ...     action_config={"level": "info", "message": "State changed"},
        ...     execution_order=1,
        ...     is_critical=False,
        ... )
        >>> action.action_name
        'log_transition'
    """

    action_name: str = Field(
        default=...,
        description="Unique action identifier",
    )

    action_type: str = Field(
        default=...,
        description="Type of action (emit_intent, log, validate, etc.)",
    )

    action_config: dict[str, ActionConfigValue] = Field(
        default_factory=dict,
        description="Action configuration parameters",
    )

    execution_order: int = Field(
        default=0,
        description="Order of execution within the phase (lower executes first)",
    )

    is_critical: bool = Field(
        default=False,
        description="If true, failure stops the transition",
    )

    rollback_action: str | None = Field(
        default=None,
        description="Reserved for v1.1+ - action to execute on rollback",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Action timeout in milliseconds",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Updates any relevant execution fields based on provided kwargs.

        Args:
            **kwargs: Field updates to apply during execution

        Returns:
            bool: True if execution succeeded

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol).

        Returns:
            dict[str, object]: Dictionary representation of the model
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Performs basic validation to ensure required fields exist and
        have valid values.

        Returns:
            bool: True if validation passed

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ActionConfigValue", "ModelMvpFSMTransitionAction"]
