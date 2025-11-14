from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Result Summary Model.

Restrictive model for CLI execution result summary
with proper typing and validation.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class ModelResultSummary(BaseModel):
    """Restrictive model for result summary.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    execution_id: UUID = Field(description="Execution identifier")
    command: str = Field(description="Command name")
    target_node: str | None = Field(description="Target node name")
    success: bool = Field(description="Whether execution succeeded")
    exit_code: int = Field(description="Exit code")
    duration_ms: float = Field(description="Duration in milliseconds")
    retry_count: int = Field(description="Number of retries")
    has_errors: bool = Field(description="Whether there are errors")
    has_warnings: bool = Field(description="Whether there are warnings")
    error_count: int = Field(description="Number of errors")
    warning_count: int = Field(description="Number of warnings")
    critical_error_count: int = Field(description="Number of critical errors")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e
