from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
Strongly-typed effect operation parameters model.

Replaces primitive soup pattern with discriminated effect parameter types.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError
from omnibase_core.models.operations.model_effect_parameter_value import (
    ModelEffectParameterValue,
)


class ModelEffectParameters(BaseModel):
    """
    Strongly-typed effect operation parameters with discriminated unions.

    Replaces primitive soup pattern with discriminated effect parameter types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Use discriminated union for effect parameters
    effect_parameters: dict[str, ModelEffectParameterValue] = Field(
        default_factory=dict,
        description="Effect parameters with discriminated union types",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
            error_code=ModelCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> dict[str, object]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelEffectParameters"]
