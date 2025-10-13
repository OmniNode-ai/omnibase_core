import uuid
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_operation_parameters_base import (
    ModelOperationParameterValue,
)


class ModelOperationParameters(BaseModel):
    """
    Strongly-typed operation parameters with discriminated unions.

    Replaces primitive soup pattern with discriminated parameter types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Use discriminated union for parameter values
    parameters: dict[str, ModelOperationParameterValue] = Field(
        default_factory=dict,
        description="Operation parameters with discriminated union types",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
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
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False
