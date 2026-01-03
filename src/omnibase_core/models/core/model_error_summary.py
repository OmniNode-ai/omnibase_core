"""
Error summary model to replace dictionary usage for get_error_summary() returns.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelErrorSummary(BaseModel):
    """
    Error summary with typed fields.
    Replaces dictionary for get_error_summary() returns.
    """

    # Error identification
    error_code: str = Field(default=..., description="Error code")
    error_type: str = Field(default=..., description="Error type/category")
    error_message: str = Field(default=..., description="Human-readable error message")

    # Error context
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When error occurred",
    )
    component: str | None = Field(
        default=None, description="Component where error occurred"
    )
    operation: str | None = Field(default=None, description="Operation that failed")

    # Error details
    stack_trace: str | None = Field(
        default=None, description="Stack trace if available"
    )
    inner_errors: list[dict[str, str]] | None = Field(
        default_factory=list,
        description="Nested/inner errors",
    )
    context_data: dict[str, str] | None = Field(
        default_factory=dict,
        description="Additional context",
    )

    # Impact and resolution
    impact_level: str | None = Field(
        default=None,
        description="Impact level (low/medium/high/critical)",
    )
    affected_resources: list[str] | None = Field(
        default_factory=list,
        description="Affected resources",
    )
    suggested_actions: list[str] | None = Field(
        default_factory=list,
        description="Suggested resolution actions",
    )

    # Tracking
    error_id: UUID | None = Field(default=None, description="Unique error instance ID")
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracing",
    )
    has_been_reported: bool = Field(
        default=False, description="Whether error was reported"
    )

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, object] | None) -> "ModelErrorSummary | None":
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        # Pydantic validates the data at runtime - type safety is enforced by Pydantic
        return cls.model_validate(dict(data))

    @field_serializer("occurred_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
