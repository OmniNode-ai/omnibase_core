"""
FSM Transition Action Model for state/transition actions.

Defines action specifications for FSM state transitions, including
action types, configuration, and execution order for determining
actions to execute during state transitions.

Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md

Type Aliases:
    ActionConfigValue: Union type for action configuration values.
        Supports primitive types (str, int, float, bool), lists of strings,
        and None for FSM action configuration parameters.

Note:
    This model is part of the FSM v1.0 implementation. The following fields
    are reserved for future versions and have no effect in v1.0:
    - rollback_action: Reserved for v1.1+ (rollback NOT executed)
    - execute() method: Reserved for v1.1+ (always returns True in v1.0)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Type alias for action configuration values
# Supports primitive types and lists of strings for FSM action configuration
ActionConfigValue = str | int | float | bool | list[str] | None


class ModelFSMTransitionAction(BaseModel):
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
        >>> action = ModelFSMTransitionAction(
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
        ge=0,
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
        gt=0,
        description="Action timeout in milliseconds (must be positive if set)",
    )

    model_config = {
        "extra": "ignore",
        "frozen": True,
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute action (Executable protocol).

        Reserved for v1.1+ implementation. In v1.0, this method is a no-op
        that always returns True. Actual action execution will be implemented
        in v1.1+ when the FSM runtime supports action execution hooks.

        Note:
            This model is frozen (immutable) for thread safety. The v1.1+
            implementation will use external state management rather than
            modifying the model instance.

        Args:
            **kwargs: Reserved for v1.1+ - execution parameters (currently ignored)

        Returns:
            bool: Always True in v1.0 (reserved for v1.1+ implementation)
        """
        # v1.1+ reserved: Implement action execution with external state management
        # The model is frozen for thread safety, so execution state must be
        # tracked externally (e.g., in the FSM runtime context)
        _ = kwargs  # Explicitly mark as unused for v1.0
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol).

        Returns:
            dict[str, object]: Dictionary representation of the model
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Performs validation to ensure required fields exist and have valid values:
        - action_name must be a non-empty string
        - action_type must be a non-empty string
        - action_config values must be valid ActionConfigValue types

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate action_name is non-empty
        if not self.action_name or not self.action_name.strip():
            return False

        # Validate action_type is non-empty
        if not self.action_type or not self.action_type.strip():
            return False

        # Validate action_config values are valid ActionConfigValue types
        # Note: The dict[str, ActionConfigValue] type annotation ensures type safety
        # at compile time. This runtime check validates list contents specifically
        # since list[str] can't be validated at runtime without iteration.
        for value in self.action_config.values():
            # Check list type - must be list of strings (runtime validation)
            if isinstance(value, list) and not all(
                isinstance(item, str) for item in value
            ):
                return False

        return True


# Export for use
__all__ = ["ActionConfigValue", "ModelFSMTransitionAction"]
