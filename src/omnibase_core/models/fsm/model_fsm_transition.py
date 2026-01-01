"""
Strongly-typed FSM transition model.

Replaces dict[str, Any] usage in FSM transition operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.

Deep Immutability:
    This model uses frozen=True for Pydantic immutability, and also uses
    immutable types (tuple instead of list) for deep immutability. This
    ensures that nested collections cannot be modified after construction.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_validators import convert_list_to_tuple


class ModelFsmTransition(BaseModel):
    """
    Strongly-typed FSM transition with deep immutability.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Deep Immutability:
        All collection fields use immutable types:
        - conditions: tuple[str, ...] instead of list[str]
        - actions: tuple[str, ...] instead of list[str]

        Validators automatically convert incoming lists to frozen tuples
        for convenience during model construction.
    """

    from_state: str = Field(
        default=..., min_length=1, description="Source state of transition"
    )
    to_state: str = Field(
        default=..., min_length=1, description="Target state of transition"
    )
    trigger: str = Field(
        default=..., min_length=1, description="Event that triggers the transition"
    )
    conditions: tuple[str, ...] = Field(
        default=(), description="Conditions for transition"
    )
    actions: tuple[str, ...] = Field(
        default=(), description="Actions to execute on transition"
    )

    @field_validator("conditions", mode="before")
    @classmethod
    def _convert_conditions_to_tuple(
        cls, v: list[object] | tuple[object, ...] | object
    ) -> tuple[str, ...]:
        """Convert list of conditions to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    @field_validator("actions", mode="before")
    @classmethod
    def _convert_actions_to_tuple(
        cls, v: list[object] | tuple[object, ...] | object
    ) -> tuple[str, ...]:
        """Convert list of actions to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        frozen=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Note: In v1.0, this method returns True without modification.
        The model is frozen (immutable) for thread safety.
        """
        # v1.0: Model is frozen, so setattr is not allowed
        _ = kwargs  # Explicitly mark as unused
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Validates that required fields have valid values:
        - from_state must be a non-whitespace string (min_length enforced by Pydantic)
        - to_state must be a non-whitespace string (min_length enforced by Pydantic)
        - trigger must be a non-whitespace string (min_length enforced by Pydantic)

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate from_state is not whitespace-only
        if not self.from_state.strip():
            return False
        # Validate to_state is not whitespace-only
        if not self.to_state.strip():
            return False
        # Validate trigger is not whitespace-only
        if not self.trigger.strip():
            return False
        return True


# Export for use
__all__ = ["ModelFsmTransition"]
