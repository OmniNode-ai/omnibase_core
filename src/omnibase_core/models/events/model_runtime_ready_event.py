"""
Event model for runtime ready state.

Published when the ONEX runtime is fully initialized and all
nodes are wired to their event bus subscriptions.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field, model_validator

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

    @model_validator(mode="after")
    def validate_node_count_consistency(self) -> "ModelRuntimeReadyEvent":
        """Validate that node_count matches len(nodes_wired) when both are provided."""
        # Only validate if nodes_wired list is non-empty and node_count was explicitly set
        # This allows node_count=0 with empty nodes_wired list (default case)
        if self.nodes_wired and self.node_count != len(self.nodes_wired):
            msg = (
                f"node_count ({self.node_count}) does not match "
                f"len(nodes_wired) ({len(self.nodes_wired)})"
            )
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(msg)
        return self

    @classmethod
    def create(
        cls,
        *,
        runtime_id: UUID | None = None,
        node_count: int | None = None,
        subscription_count: int = 0,
        initialization_duration_ms: float | None = None,
        event_bus_type: str = "inmemory",
        nodes_wired: list[str] | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelRuntimeReadyEvent":
        """Factory method for creating a runtime ready event.

        Args:
            runtime_id: Unique identifier for this runtime instance.
            node_count: Total number of nodes wired. If None and nodes_wired
                is provided, derived from len(nodes_wired).
            subscription_count: Total number of subscriptions created.
            initialization_duration_ms: How long initialization took.
            event_bus_type: Type of event bus being used.
            nodes_wired: List of node names that were wired.
            correlation_id: Correlation ID for request tracing.

        Returns:
            A new ModelRuntimeReadyEvent instance.
        """
        nodes_wired_list = nodes_wired if nodes_wired is not None else []
        # Derive node_count from nodes_wired if not explicitly provided
        actual_node_count = (
            node_count if node_count is not None else len(nodes_wired_list)
        )
        return cls(
            runtime_id=runtime_id or uuid4(),
            node_count=actual_node_count,
            subscription_count=subscription_count,
            initialization_duration_ms=initialization_duration_ms,
            event_bus_type=event_bus_type,
            nodes_wired=nodes_wired_list,
            correlation_id=correlation_id,
        )
