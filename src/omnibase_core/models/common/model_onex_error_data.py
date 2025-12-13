"""
Internal Pydantic model for ONEX error serialization and validation.

This model provides structured error information with validation,
serialization, and schema generation capabilities. Used internally
by ModelOnexError exception class.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_error_code import EnumOnexErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class _ModelOnexErrorData(BaseModel):
    """
    Internal Pydantic model for ONEX error serialization and validation.

    This model provides structured error information with validation,
    serialization, and schema generation capabilities. Used internally
    by ModelOnexError exception class.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "File not found: config.yaml",
                "error_code": "ONEX_CORE_021_FILE_NOT_FOUND",
                "status": "error",
                "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-25T22:30:00Z",
                "context": {"file_path": "/path/to/config.yaml"},
            },
        },
    )

    message: str = Field(
        default=...,
        description="Human-readable error message",
        json_schema_extra={"example": "File not found: config.yaml"},
    )
    error_code: str | EnumOnexErrorCode | None = Field(
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
        json_schema_extra={"example": "req-123e4567-e89b-12d3-a456-426614174000"},
    )
    timestamp: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the error occurred",
        json_schema_extra={"example": "2025-05-25T22:30:00Z"},
    )
    context: dict[str, object] = Field(
        default_factory=dict,
        description="Additional context information for the error (JSON-serializable values)",
        json_schema_extra={"example": {"file_path": "/path/to/config.yaml"}},
    )


# Export for use
__all__ = []
