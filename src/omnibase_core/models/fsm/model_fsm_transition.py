from __future__ import annotations

from pydantic import Field

"""
Strongly-typed FSM transition model.

Replaces dict[str, Any] usage in FSM transition operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from pydantic import BaseModel


class ModelFsmTransition(BaseModel):
    """
    Strongly-typed FSM transition.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    from_state: str = Field(default=..., description="Source state of transition")
    to_state: str = Field(default=..., description="Target state of transition")
    trigger: str = Field(default=..., description="Event that triggers the transition")
    conditions: list[str] = Field(
        default_factory=list, description="Conditions for transition"
    )
    actions: list[str] = Field(
        default_factory=list, description="Actions to execute on transition"
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "frozen": True,
    }

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
        - from_state must be a non-empty, non-whitespace string
        - to_state must be a non-empty, non-whitespace string
        - trigger must be a non-empty, non-whitespace string

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate from_state is non-empty
        if not self.from_state or not self.from_state.strip():
            return False
        # Validate to_state is non-empty
        if not self.to_state or not self.to_state.strip():
            return False
        # Validate trigger is non-empty
        if not self.trigger or not self.trigger.strip():
            return False
        return True


# Export for use
__all__ = ["ModelFsmTransition"]
