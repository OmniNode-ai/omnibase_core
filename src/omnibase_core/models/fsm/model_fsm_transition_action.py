"""
FSM Transition Action Model for state/transition actions.

Defines action specifications for FSM state transitions, including
action types, configuration, and execution order for determining
actions to execute during state transitions.

Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md

Action Config Value Type:
    Action configuration values support primitive types (str, int, float, bool),
    tuples of strings, and None for FSM action configuration parameters.
    The full type is: str | int | float | bool | tuple[str, ...] | None

Deep Immutability:
    This model uses frozen=True for Pydantic immutability, and also uses
    immutable types (tuple instead of list/dict) for deep immutability.
    This ensures that nested collections cannot be modified after construction.

Note:
    This model is part of the FSM v1.0 implementation. The following fields
    are reserved for future versions and have no effect in v1.0:
    - rollback_action: Reserved for v1.1+ (rollback NOT executed)
    - execute() method: Reserved for v1.1+ (always returns True in v1.0)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelFSMTransitionAction(BaseModel):
    """
    Action specification for FSM state transitions with deep immutability.

    Defines actions to execute during state transitions, including
    action types (emit_intent, log, etc.), configuration parameters,
    and execution ordering.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Deep Immutability:
        The action_config field uses tuple[tuple[str, str | int | float | bool | tuple[str, ...] | None], ...]
        instead of dict for deep immutability. Validators automatically convert
        incoming dicts to frozen types for convenience during model construction.

    Accessing dict-like fields:
        For action_config, use dict() to convert back:
        >>> action = ModelFSMTransitionAction(
        ...     action_name="test", action_type="log",
        ...     action_config={"level": "info"}
        ... )
        >>> config_dict = dict(action.action_config)  # Convert to dict for lookup

    v1.0 Reserved Fields (parsed but NOT executed):
        - rollback_action: Parsed, but rollback NOT executed until v1.1

    Setting rollback_action in v1.0 contracts will NOT change runtime behavior.

    Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md

    Attributes:
        action_name: Unique identifier for the action (required)
        action_type: Type of action (emit_intent, log, etc.) (required)
        action_config: Configuration as frozen key-value pairs (immutable)
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
        min_length=1,
        description="Unique action identifier",
    )

    action_type: str = Field(
        default=...,
        min_length=1,
        description="Type of action (emit_intent, log, validate, etc.)",
    )

    action_config: tuple[
        tuple[str, str | int | float | bool | tuple[str, ...] | None], ...
    ] = Field(
        default=(),
        description="Action configuration parameters as frozen key-value pairs",
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

    @field_validator("action_config", mode="before")
    @classmethod
    def _convert_action_config_to_frozen(
        cls,
        v: (
            dict[str, str | int | float | bool | tuple[str, ...] | None]
            | tuple[tuple[str, str | int | float | bool | tuple[str, ...] | None], ...]
            | None
        ),
    ) -> tuple[tuple[str, str | int | float | bool | tuple[str, ...] | None], ...]:
        """Convert dict to tuple of tuples for deep immutability.

        Also converts any list values to tuples for complete immutability.
        """
        if v is None:
            return ()
        if isinstance(v, dict):
            # Convert dict to tuple of tuples, also converting list values to tuples
            return tuple(
                (k, tuple(val) if isinstance(val, list) else val)
                for k, val in v.items()
            )
        return v

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )

    # Protocol method implementations

    def execute(self, **_kwargs: object) -> bool:
        """Execute action (Executable protocol).

        Reserved for v1.1+ implementation. In v1.0, this method is a no-op
        that always returns True. Actual action execution will be implemented
        in v1.1+ when the FSM runtime supports action execution hooks.

        Note:
            This model is frozen (immutable) for thread safety. The v1.1+
            implementation will use external state management rather than
            modifying the model instance.

        Args:
            **_kwargs: Reserved for v1.1+ - execution parameters (currently unused)

        Returns:
            bool: Always True in v1.0 (reserved for v1.1+ implementation)
        """
        # v1.1+ reserved: Implement action execution with external state management
        # The model is frozen for thread safety, so execution state must be
        # tracked externally (e.g., in the FSM runtime context)
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
        - action_config values must be valid types (str, int, float, bool, tuple[str, ...], or None)

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate action_name is non-empty
        if not self.action_name or not self.action_name.strip():
            return False

        # Validate action_type is non-empty
        if not self.action_type or not self.action_type.strip():
            return False

        # Validate action_config values are valid types
        # Note: action_config is tuple[tuple[str, str | int | float | bool | tuple[str, ...] | None], ...]
        # for deep immutability. This runtime check validates tuple contents
        # since tuple[str, ...] can't be validated at runtime without iteration.
        for _key, value in self.action_config:
            # Check tuple type - must be tuple of strings (runtime validation)
            if isinstance(value, tuple) and not all(
                isinstance(item, str) for item in value
            ):
                return False

        return True


# Export for use
__all__ = ["ModelFSMTransitionAction"]
