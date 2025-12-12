from __future__ import annotations

"""
Strongly-typed FSM state model.

Replaces dict[str, Any] usage in FSM state operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelFsmState(BaseModel):
    """
    Strongly-typed FSM state.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    name: str = Field(default=..., description="State name")
    description: str = Field(default="", description="State description")
    is_initial: bool = Field(
        default=False, description="Whether this is the initial state"
    )
    is_final: bool = Field(default=False, description="Whether this is a final state")
    entry_actions: list[str] = Field(
        default_factory=list, description="Actions on state entry"
    )
    exit_actions: list[str] = Field(
        default_factory=list, description="Actions on state exit"
    )
    properties: dict[str, str] = Field(
        default_factory=dict, description="State properties"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        frozen=True,
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
        - name must be a non-empty, non-whitespace string

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate name is non-empty and non-whitespace
        if not self.name or not self.name.strip():
            return False
        return True


# Export for use
__all__ = ["ModelFsmState"]
