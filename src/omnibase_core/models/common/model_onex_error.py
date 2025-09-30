"""
Canonical Pydantic model for ONEX error serialization and validation.

This model provides structured error information with validation,
serialization, and schema generation capabilities across all ONEX components.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.common.model_error_context import ModelErrorContext


class ModelOnexError(BaseModel):
    """
    Canonical Pydantic model for ONEX error serialization and validation.

    This model provides structured error information with validation,
    serialization, and schema generation capabilities.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    message: str = Field(
        ...,
        description="Human-readable error message",
        json_schema_extra={"example": "File not found: config.yaml"},
    )
    error_code: str | None = Field(
        default=None,
        description="Canonical error code for this error",
        json_schema_extra={"example": "ONEX_CORE_021_FILE_NOT_FOUND"},
    )
    status: EnumOnexStatus = Field(
        default=EnumOnexStatus.ERROR,
        description="EnumOnexStatus for this error",
        json_schema_extra={"example": "error"},
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for request tracking",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )
    timestamp: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the error occurred",
        json_schema_extra={"example": "2025-05-25T22:30:00Z"},
    )
    context: ModelErrorContext = Field(
        default_factory=lambda: ModelErrorContext(
            file_path=None,
            line_number=None,
            column_number=None,
            function_name=None,
            module_name=None,
            stack_trace=None,
            additional_context={},
        ),
        description="Additional context information for the error",
        json_schema_extra={"example": {"file_path": "/path/to/config.yaml"}},
    )

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False
