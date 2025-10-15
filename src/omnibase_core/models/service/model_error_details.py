from typing import Dict, Optional
from uuid import UUID

from pydantic import Field

"""
Error details model to replace Dict[str, Any] usage.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class ModelErrorDetails(BaseModel):
    """
    Error details with typed fields.
    Replaces Dict[str, Any] for error_details fields.
    """

    # Error identification
    error_code: str = Field(default=..., description="Error code")
    error_type: str = Field(
        default=..., description="Error type (validation/runtime/system)"
    )
    error_message: str = Field(default=..., description="Error message")

    # Error context
    component: str | None = Field(
        default=None, description="Component where error occurred"
    )
    operation: str | None = Field(default=None, description="Operation being performed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp",
    )

    # Error details
    stack_trace: list[str] | None = Field(default=None, description="Stack trace lines")
    inner_errors: list["ModelErrorDetails"] | None = Field(
        default=None,
        description="Nested errors",
    )

    # Contextual data
    request_id: UUID | None = Field(default=None, description="Request ID")
    user_id: UUID | None = Field(default=None, description="User ID")
    session_id: UUID | None = Field(default=None, description="Session ID")

    # Additional context
    context_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context",
    )

    # Recovery information
    retry_after_seconds: int | None = Field(
        default=None, description="Retry after seconds"
    )
    recovery_suggestions: list[str] | None = Field(
        default=None,
        description="Recovery suggestions",
    )
    documentation_url: str | None = Field(default=None, description="Documentation URL")

    model_config = ConfigDict()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ModelErrorDetails"]:
        """Create from dict[str, Any]ionary for easy migration."""
        if data is None:
            return None

        # Handle legacy format
        if "error_code" not in data and "code" in data:
            data["error_code"] = data.pop("code")
        if "error_type" not in data:
            data["error_type"] = "runtime"
        if "error_message" not in data and "message" in data:
            data["error_message"] = data.pop("message")

        return cls(**data)

    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        return self.retry_after_seconds is not None or self.error_type in [
            "timeout",
            "rate_limit",
        ]

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
