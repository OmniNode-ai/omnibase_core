"""
Canonical Pydantic model for ONEX error serialization and validation.

This model provides structured error information with validation,
serialization, and schema generation capabilities across all ONEX components.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.core.model_error_context import ModelErrorContext


class ModelOnexError(BaseModel):
    """
    Canonical Pydantic model for ONEX error serialization and validation.

    This model provides structured error information with validation,
    serialization, and schema generation capabilities.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "File not found: config.yaml",
                "error_code": "ONEX_CORE_021_FILE_NOT_FOUND",
                "status": "error",
                "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "context": {
                    "file_path": "/path/to/config.yaml",
                    "operation": "file_read",
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    )

    # Core error information
    message: str = Field(
        ...,
        description="Human-readable error message",
        min_length=1,
        max_length=512
    )

    error_code: str = Field(
        ...,
        description="Machine-readable error code following ONEX conventions",
        pattern="^[A-Z_][A-Z0-9_]*$",
        min_length=1,
        max_length=128
    )

    status: EnumOnexStatus = Field(
        ...,
        description="Error status classification"
    )

    # Optional context and metadata
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for request tracing",
        min_length=1,
        max_length=128
    )

    context: ModelErrorContext | None = Field(
        None,
        description="Additional error context information"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred (UTC)"
    )

    # Optional nested error for error chains
    caused_by: "ModelOnexError | None" = Field(
        None,
        description="Underlying error that caused this error"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result: dict[str, Any] = {
            "message": self.message,
            "error_code": self.error_code,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat()
        }

        if self.correlation_id:
            result["correlation_id"] = self.correlation_id

        if self.context:
            result["context"] = self.context.model_dump() if hasattr(self.context, 'model_dump') else dict(self.context)

        if self.caused_by:
            result["caused_by"] = self.caused_by.to_dict()

        return result

    def __str__(self) -> str:
        """String representation for logging."""
        parts = [f"{self.error_code}: {self.message}"]

        if self.correlation_id:
            parts.append(f"[{self.correlation_id}]")

        if self.context:
            parts.append(f"Context: {self.context}")

        return " ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"ModelOnexError(error_code='{self.error_code}', message='{self.message}', status='{self.status.value}')"