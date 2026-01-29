"""Contract deregistration event model.

Published when a node deregisters its contract (graceful shutdown).
Part of the contract registration subsystem (OMN-1651).
"""

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import ModelRuntimeEventBase
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelContractDeregisteredEvent", "CONTRACT_DEREGISTERED_EVENT"]

CONTRACT_DEREGISTERED_EVENT = "onex.evt.contract-deregistered.v1"


class ModelContractDeregisteredEvent(ModelRuntimeEventBase):
    """Contract deregistration event (graceful shutdown).

    Published when a node gracefully deregisters its contract,
    typically during shutdown, upgrade, or manual removal.

    Inherits from ModelRuntimeEventBase:
        event_id, correlation_id, timestamp, source_node_id
    """

    event_type: str = Field(
        default=CONTRACT_DEREGISTERED_EVENT,
        description="Event type identifier",
    )
    node_name: str = Field(
        description="Name of the deregistering node",
    )
    node_version: ModelSemVer = Field(
        description="Semantic version of the deregistering node",
    )
    reason: str = Field(
        description="Reason for deregistration: 'shutdown', 'upgrade', 'manual'",
    )
