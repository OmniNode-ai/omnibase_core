"""
Error details model to replace Dict[str, Any] usage.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelErrorDetails(BaseModel):
    """
    Error details with typed fields.
    Replaces Dict[str, Any] for error_details fields.
    """

    # Error identification
    error_code: str = Field(..., description="Error code")
    error_type: str = Field(..., description="Error type (validation/runtime/system)")
    error_message: str = Field(..., description="Error message")

    # Error context
    component: Optional[str] = Field(None, description="Component where error occurred")
    operation: Optional[str] = Field(None, description="Operation being performed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )

    # Error details
    stack_trace: Optional[List[str]] = Field(None, description="Stack trace lines")
    inner_errors: Optional[List["ModelErrorDetails"]] = Field(
        None, description="Nested errors"
    )

    # Contextual data
    request_id: Optional[str] = Field(None, description="Request ID")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")

    # Additional context
    context_data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional error context"
    )

    # Recovery information
    retry_after_seconds: Optional[int] = Field(None, description="Retry after seconds")
    recovery_suggestions: Optional[List[str]] = Field(
        None, description="Recovery suggestions"
    )
    documentation_url: Optional[str] = Field(None, description="Documentation URL")

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["ModelErrorDetails"]:
        """Create from dictionary for easy migration."""
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
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
