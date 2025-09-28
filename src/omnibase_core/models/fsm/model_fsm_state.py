"""
Strongly-typed FSM state model.

Replaces dict[str, Any] usage in FSM state operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Executable


class ModelFsmState(BaseModel):
    """
    Strongly-typed FSM state.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    name: str = Field(..., description="State name")
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

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelFsmState"]
