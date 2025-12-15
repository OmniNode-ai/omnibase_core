"""
Event model for runtime ready state.

Published when the ONEX runtime is fully initialized and all
nodes are wired to their event bus subscriptions.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelRuntimeReadyEvent", "RUNTIME_READY_EVENT"]

RUNTIME_READY_EVENT = "onex.runtime.ready"


class ModelRuntimeReadyEvent(ModelRuntimeEventBase):
    """
    Event published when the ONEX runtime is fully initialized.

    Indicates that all nodes are wired and the system is ready
    to process events.
    """

    event_type: str = Field(
        default=RUNTIME_READY_EVENT,
        description="Event type identifier",
    )
    runtime_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this runtime instance",
    )
    node_count: int = Field(
        default=0,
        ge=0,
        description="Total number of nodes wired",
    )
    subscription_count: int = Field(
        default=0,
        ge=0,
        description="Total number of subscriptions created",
    )
    ready_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the runtime became ready (UTC)",
    )
    initialization_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="How long initialization took in milliseconds",
    )
    event_bus_type: str = Field(
        default="inmemory",
        description="Type of event bus being used",
    )
    nodes_wired: list[str] = Field(
        default_factory=list,
        description="List of node names that were wired",
    )

    @classmethod
    def create(
        cls,
        *,
        runtime_id: UUID | None = None,
        node_count: int = 0,
        subscription_count: int = 0,
        initialization_duration_ms: float | None = None,
        event_bus_type: str = "inmemory",
        nodes_wired: list[str] | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelRuntimeReadyEvent":
        """Factory method for creating a runtime ready event."""
        return cls(
            runtime_id=runtime_id or uuid4(),
            node_count=node_count,
            subscription_count=subscription_count,
            initialization_duration_ms=initialization_duration_ms,
            event_bus_type=event_bus_type,
            nodes_wired=nodes_wired if nodes_wired is not None else [],
            correlation_id=correlation_id,
        )
