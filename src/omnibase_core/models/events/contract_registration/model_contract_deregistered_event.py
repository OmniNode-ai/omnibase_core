"""Contract deregistration event model.

Published when a node deregisters its contract (graceful shutdown).
Part of the contract registration subsystem (OMN-1651).
"""

from pydantic import ConfigDict, Field

from omnibase_core.enums.events.enum_deregistration_reason import (
    EnumDeregistrationReason,
)
from omnibase_core.models.events.model_runtime_event_base import ModelRuntimeEventBase
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelContractDeregisteredEvent", "CONTRACT_DEREGISTERED_EVENT"]

# Full topic name for Kafka/event bus publishing (onex.evt.<type>.v1 format).
# The short event type identifier ("contract-deregistered") is in constants_event_types.py.
CONTRACT_DEREGISTERED_EVENT = "onex.evt.contract-deregistered.v1"


class ModelContractDeregisteredEvent(ModelRuntimeEventBase):
    """Contract deregistration event (graceful shutdown).

    Published when a node gracefully deregisters its contract,
    typically during shutdown, upgrade, or manual removal.

    Inherits from ModelRuntimeEventBase:
        event_id, correlation_id, timestamp, source_node_id
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

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
    reason: EnumDeregistrationReason = Field(
        description="Reason for deregistration (SHUTDOWN, UPGRADE, or MANUAL)",
    )
