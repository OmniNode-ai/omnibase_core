"""
Pydantic model for ONEX warning serialization and validation.

This model provides structured warning information with validation,
serialization, and schema generation capabilities.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class ModelOnexWarning(BaseModel):
    """
    Pydantic model for ONEX warning serialization and validation.

    This model provides structured warning information with validation,
    serialization, and schema generation capabilities.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "File already exists and will be overwritten: config.yaml",
                "warning_code": "ONEX_CORE_W001_FILE_OVERWRITE",
                "status": "warning",
                "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-25T22:30:00Z",
                "context": {"file_path": "/path/to/config.yaml"},
            },
        },
    )

    message: str = Field(
        default=...,
        description="Human-readable warning message",
        json_schema_extra={
            "example": "File already exists and will be overwritten: config.yaml",
        },
    )
    warning_code: str | None = Field(
        default=None,
        description="Canonical warning code for this warning",
        json_schema_extra={"example": "ONEX_CORE_W001_FILE_OVERWRITE"},
    )
    status: EnumOnexStatus = Field(
        default=EnumOnexStatus.WARNING,
        description="EnumOnexStatus for this warning",
        json_schema_extra={"example": "warning"},
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for request tracking",
        json_schema_extra={"example": "req-123e4567-e89b-12d3-a456-426614174000"},
    )
    timestamp: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the warning occurred",
        json_schema_extra={"example": "2025-05-25T22:30:00Z"},
    )
    context: dict[str, object] = Field(
        default_factory=dict,
        description="Additional context information for the warning (JSON-serializable values)",
        json_schema_extra={"example": {"file_path": "/path/to/config.yaml"}},
    )


# Export for use
__all__ = [
    "ModelOnexWarning",
]
