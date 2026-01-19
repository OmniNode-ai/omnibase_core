"""MCP invocation request model.

Tool call request envelope for MCP protocol.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelMCPInvocationRequest(BaseModel):
    """Request model for MCP tool invocation.

    Represents an incoming tool call from an AI agent via the MCP protocol.
    This is the standard envelope for all tool invocations.

    Attributes:
        tool_name: Name of the tool to invoke.
        arguments: Tool parameters as key-value pairs.
        correlation_id: Optional correlation ID for request tracing.
        request_id: Unique identifier for this specific request.
        timeout_ms: Optional timeout override in milliseconds.
        metadata: Additional request metadata.
    """

    tool_name: str = Field(..., description="Name of the tool to invoke")
    arguments: dict[str, object] = Field(
        default_factory=dict, description="Tool parameters as key-value pairs"
    )
    correlation_id: UUID | None = Field(
        default=None, description="Optional correlation ID for request tracing"
    )
    request_id: UUID | None = Field(
        default=None, description="Unique identifier for this specific request"
    )
    timeout_ms: int | None = Field(
        default=None, description="Optional timeout override in milliseconds", ge=0
    )
    metadata: dict[str, object] = Field(
        default_factory=dict, description="Additional request metadata"
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    def has_correlation_id(self) -> bool:
        """Check if a correlation ID is set.

        Returns:
            True if correlation_id is not None.
        """
        return self.correlation_id is not None

    def get_argument(self, key: str, default: object = None) -> object:
        """Get an argument value by key.

        Args:
            key: Argument key to retrieve.
            default: Default value if key not found.

        Returns:
            Argument value or default.
        """
        return self.arguments.get(key, default)


__all__ = ["ModelMCPInvocationRequest"]
