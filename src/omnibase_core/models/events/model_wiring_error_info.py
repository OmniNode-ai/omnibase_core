"""
Typed model for wiring error information.

Provides a strongly-typed model for error details in wiring
result events, replacing dict[str, Any] patterns.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelWiringErrorInfo"]


class ModelWiringErrorInfo(BaseModel):
    """
    Typed error information for wiring result events.

    Replaces dict[str, Any] in wiring result events with explicit
    typed fields for error tracking and debugging.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        from_attributes=True,
    )

    node_id: UUID | None = Field(
        default=None,
        description="Node that encountered the error (if applicable)",
    )
    topic: str | None = Field(
        default=None,
        description="Topic related to the error (if applicable)",
    )
    error_code: str = Field(
        description="Error code identifying the failure type",
    )
    error_message: str = Field(
        description="Human-readable error description",
    )
    retryable: bool = Field(
        default=False,
        description="Whether this error is retryable",
    )
