"""MCP invocation response model.

Tool call response wrapper for MCP protocol.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelMCPInvocationResponse(BaseModel):
    """Response model for MCP tool invocation.

    Represents the response from a tool invocation to be returned via MCP.
    This is the standard envelope for all tool responses.

    Attributes:
        success: Whether the tool execution succeeded.
        content: The result content (string, dict, or list).
        is_error: Whether this result represents an error.
        error_message: Error details if is_error is True.
        error_code: Machine-readable error code.
        correlation_id: Correlation ID from the original request.
        request_id: Request ID from the original request.
        execution_time_ms: Execution duration in milliseconds.
        metadata: Additional response metadata.
    """

    success: bool = Field(..., description="Whether the tool execution succeeded")
    content: str | dict[str, object] | list[object] = Field(
        ..., description="The result content (string, dict, or list)"
    )
    is_error: bool = Field(
        default=False, description="Whether this result represents an error"
    )
    error_message: str | None = Field(
        default=None, description="Error details if is_error is True"
    )
    error_code: str | None = Field(
        default=None, description="Machine-readable error code"
    )
    correlation_id: UUID | None = Field(
        default=None, description="Correlation ID from the original request"
    )
    request_id: UUID | None = Field(
        default=None, description="Request ID from the original request"
    )
    execution_time_ms: float | None = Field(
        default=None,
        description="Execution duration in milliseconds (sub-ms precision)",
        ge=0.0,
    )
    metadata: dict[str, object] = Field(
        default_factory=dict, description="Additional response metadata"
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    def __bool__(self) -> bool:
        """Return True if the invocation was successful.

        Warning:
            This overrides standard Pydantic behavior where bool(model)
            always returns True. This model returns True only when
            success is True and is_error is False.

        Returns:
            True if success is True and is_error is False.
        """
        return self.success and not self.is_error

    @classmethod
    def success_response(
        cls,
        content: str | dict[str, object] | list[object],
        *,
        correlation_id: UUID | None = None,
        request_id: UUID | None = None,
        execution_time_ms: float | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ModelMCPInvocationResponse:
        """Create a successful response.

        Args:
            content: The result content.
            correlation_id: Optional correlation ID.
            request_id: Optional request ID.
            execution_time_ms: Optional execution time.
            metadata: Optional metadata.

        Returns:
            A successful response instance.
        """
        return cls(
            success=True,
            content=content,
            is_error=False,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )

    @classmethod
    def error_response(
        cls,
        error_message: str,
        *,
        error_code: str | None = None,
        correlation_id: UUID | None = None,
        request_id: UUID | None = None,
        execution_time_ms: float | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ModelMCPInvocationResponse:
        """Create an error response.

        Args:
            error_message: Error description.
            error_code: Optional machine-readable error code.
            correlation_id: Optional correlation ID.
            request_id: Optional request ID.
            execution_time_ms: Optional execution time.
            metadata: Optional metadata.

        Returns:
            An error response instance.
        """
        return cls(
            success=False,
            content=error_message,
            is_error=True,
            error_message=error_message,
            error_code=error_code,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )


__all__ = ["ModelMCPInvocationResponse"]
