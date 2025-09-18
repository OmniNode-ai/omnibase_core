"""
ONEX Warning Model

Pydantic model for ONEX warning messages with structured information.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.core.model_error_context import ModelErrorContext


class ModelOnexWarning(BaseModel):
    """
    Pydantic model for ONEX warning messages.

    Provides structured warning information similar to ModelOnexError
    but for non-blocking issues that should be noted.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Configuration value may be deprecated",
                "warning_code": "ONEX_CORE_W001_DEPRECATED_CONFIG",
                "status": "warning",
                "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-25T22:30:00Z",
                "context": {"config_key": "legacy_timeout_setting"},
            },
        },
    )

    message: str = Field(
        ...,
        description="Human-readable warning message",
        json_schema_extra={"example": "Configuration value may be deprecated"},
    )
    warning_code: str | None = Field(
        default=None,
        description="Canonical warning code for this warning",
        json_schema_extra={"example": "ONEX_CORE_W001_DEPRECATED_CONFIG"},
    )
    status: EnumOnexStatus = Field(
        default=EnumOnexStatus.WARNING,
        description="Status for this warning",
        json_schema_extra={"example": "warning"},
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional correlation ID for request tracking",
        json_schema_extra={"example": "req-123e4567-e89b-12d3-a456-426614174000"},
    )
    timestamp: datetime | None = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the warning occurred",
        json_schema_extra={"example": "2025-05-25T22:30:00Z"},
    )
    context: ModelErrorContext = Field(
        default_factory=ModelErrorContext,
        description="Additional context information for the warning",
        json_schema_extra={"example": {"config_key": "legacy_timeout_setting"}},
    )
    severity: str = Field(
        default="medium",
        description="Warning severity level (low, medium, high)",
        json_schema_extra={"example": "medium"},
    )
    category: str = Field(
        default="general",
        description="Warning category (configuration, performance, deprecation, etc.)",
        json_schema_extra={"example": "deprecation"},
    )
