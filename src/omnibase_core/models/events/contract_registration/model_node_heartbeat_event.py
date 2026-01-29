"""Node heartbeat event model.

Published periodically to indicate node liveness.
Part of the contract registration subsystem (OMN-1651).
"""

from pydantic import ConfigDict, Field

from omnibase_core.models.events.model_runtime_event_base import ModelRuntimeEventBase
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelNodeHeartbeatEvent", "NODE_HEARTBEAT_EVENT"]

NODE_HEARTBEAT_EVENT = "onex.evt.node-heartbeat.v1"


class ModelNodeHeartbeatEvent(ModelRuntimeEventBase):
    """Node liveness heartbeat event.

    Published periodically by registered nodes to indicate they
    are still alive and operational. Used for health monitoring
    and stale contract detection.

    Inherits from ModelRuntimeEventBase:
        event_id, correlation_id, timestamp, source_node_id

    Optional observability fields:
        sequence_number: Monotonically increasing counter for heartbeat ordering.
            Useful for detecting missed heartbeats or out-of-order delivery.
        uptime_seconds: Node uptime since last restart for availability tracking.
        contract_hash: Current contract hash for runtime drift detection.
            Enables detection of contract changes without re-registration.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

    event_type: str = Field(
        default=NODE_HEARTBEAT_EVENT,
        description="Event type identifier",
    )
    node_name: str = Field(
        description="Name of the heartbeating node",
    )
    node_version: ModelSemVer = Field(
        description="Semantic version of the heartbeating node",
    )
    sequence_number: int | None = Field(
        default=None,
        ge=0,
        description="Monotonically increasing sequence for ordering heartbeats",
    )
    uptime_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Node uptime in seconds since last restart",
    )
    contract_hash: str | None = Field(
        default=None,
        min_length=1,
        description="Current contract hash for drift detection",
    )
