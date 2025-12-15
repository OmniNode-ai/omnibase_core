"""
Event model for wiring errors.

Published when a critical wiring error occurs during
event bus subscription setup.
"""

from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelWiringErrorEvent", "WIRING_ERROR_EVENT"]

WIRING_ERROR_EVENT = "onex.runtime.wiring.error"


class ModelWiringErrorEvent(ModelRuntimeEventBase):
    """
    Event published when a critical wiring error occurs.

    Indicates that the event bus wiring process encountered
    a non-recoverable error.
    """

    event_type: str = Field(
        default=WIRING_ERROR_EVENT,
        description="Event type identifier",
    )
    error_code: str = Field(
        default=...,
        description="Error code identifying the failure type",
    )
    error_message: str = Field(
        default=...,
        description="Human-readable error description",
    )
    affected_nodes: list[str] = Field(
        default_factory=list,
        description="Nodes affected by this error",
    )
    partial_success: bool = Field(
        default=False,
        description="Whether some wiring succeeded before the error",
    )
    successful_subscriptions: int = Field(
        default=0,
        ge=0,
        description="Number of subscriptions that succeeded before error",
    )
    failed_subscriptions: int = Field(
        default=0,
        ge=0,
        description="Number of subscriptions that failed",
    )
    stack_trace: str | None = Field(
        default=None,
        description="Optional stack trace for debugging",
    )

    @classmethod
    def create(
        cls,
        error_code: str,
        error_message: str,
        *,
        affected_nodes: list[str] | None = None,
        partial_success: bool = False,
        successful_subscriptions: int = 0,
        failed_subscriptions: int = 0,
        stack_trace: str | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelWiringErrorEvent":
        """Factory method for creating a wiring error event."""
        return cls(
            error_code=error_code,
            error_message=error_message,
            affected_nodes=affected_nodes if affected_nodes is not None else [],
            partial_success=partial_success,
            successful_subscriptions=successful_subscriptions,
            failed_subscriptions=failed_subscriptions,
            stack_trace=stack_trace,
            correlation_id=correlation_id,
        )
