"""
Event model for wiring operation result.

Published as the result of a wiring operation, containing
the outcome of wiring all subscriptions for a node graph.
"""

from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)
from omnibase_core.models.events.model_wiring_error_info import (
    ModelWiringErrorInfo,
)

__all__ = ["ModelWiringResultEvent", "WIRING_RESULT_EVENT"]

WIRING_RESULT_EVENT = "onex.runtime.wiring.result"


class ModelWiringResultEvent(ModelRuntimeEventBase):
    """
    Event published as the result of a wiring operation.

    Contains the outcome of wiring all subscriptions for a
    node graph.
    """

    event_type: str = Field(
        default=WIRING_RESULT_EVENT,
        description="Event type identifier",
    )
    success: bool = Field(
        default=False,
        description="Whether the wiring operation was successful",
    )
    total_nodes: int = Field(
        default=0,
        ge=0,
        description="Total number of nodes processed",
    )
    successful_nodes: int = Field(
        default=0,
        ge=0,
        description="Number of nodes successfully wired",
    )
    failed_nodes: int = Field(
        default=0,
        ge=0,
        description="Number of nodes that failed wiring",
    )
    total_subscriptions: int = Field(
        default=0,
        ge=0,
        description="Total number of subscriptions attempted",
    )
    successful_subscriptions: int = Field(
        default=0,
        ge=0,
        description="Number of subscriptions successfully created",
    )
    failed_subscriptions: int = Field(
        default=0,
        ge=0,
        description="Number of subscriptions that failed",
    )
    wiring_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="How long the wiring process took in milliseconds",
    )
    errors: list[ModelWiringErrorInfo] = Field(
        default_factory=list,
        description="List of errors encountered during wiring",
    )

    @classmethod
    def create(
        cls,
        *,
        success: bool = False,
        total_nodes: int = 0,
        successful_nodes: int = 0,
        failed_nodes: int = 0,
        total_subscriptions: int = 0,
        successful_subscriptions: int = 0,
        failed_subscriptions: int = 0,
        wiring_duration_ms: float | None = None,
        errors: list[ModelWiringErrorInfo] | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelWiringResultEvent":
        """Factory method for creating a wiring result event."""
        return cls(
            success=success,
            total_nodes=total_nodes,
            successful_nodes=successful_nodes,
            failed_nodes=failed_nodes,
            total_subscriptions=total_subscriptions,
            successful_subscriptions=successful_subscriptions,
            failed_subscriptions=failed_subscriptions,
            wiring_duration_ms=wiring_duration_ms,
            errors=errors if errors is not None else [],
            correlation_id=correlation_id,
        )
