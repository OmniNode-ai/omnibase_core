"""Node heartbeat event model.

Published periodically to indicate node liveness.
Part of the contract registration subsystem (OMN-1651).
"""

from pydantic import Field

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
    """

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
