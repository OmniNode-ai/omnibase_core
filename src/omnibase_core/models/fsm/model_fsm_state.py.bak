from __future__ import annotations

from typing import Any

from pydantic import Field

"""
Strongly-typed FSM state model.

Replaces dict[str, Any] usage in FSM state operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from pydantic import BaseModel


class ModelFsmState(BaseModel):
    """
    Strongly-typed FSM state.
    Implements omnibase_spi protocols:
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

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
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelFsmState"]
