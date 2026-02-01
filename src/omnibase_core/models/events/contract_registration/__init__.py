"""Contract registration event models.

Event models for dynamic contract discovery via Kafka (OMN-1651).
These events enable nodes to register/deregister contracts at runtime
and provide liveness heartbeats.

Models:
    ModelContractRegisteredEvent: Contract registration with full YAML for replay.
    ModelContractDeregisteredEvent: Graceful contract deregistration.
    ModelNodeHeartbeatEvent: Node liveness heartbeat.

Event Type Constants:
    CONTRACT_REGISTERED_EVENT: "onex.evt.contract-registered.v1"
    CONTRACT_DEREGISTERED_EVENT: "onex.evt.contract-deregistered.v1"
    NODE_HEARTBEAT_EVENT: "onex.evt.node-heartbeat.v1"
"""

from omnibase_core.models.events.contract_registration.model_contract_deregistered_event import (
    CONTRACT_DEREGISTERED_EVENT,
    ModelContractDeregisteredEvent,
)
from omnibase_core.models.events.contract_registration.model_contract_registered_event import (
    CONTRACT_REGISTERED_EVENT,
    ModelContractRegisteredEvent,
)
from omnibase_core.models.events.contract_registration.model_node_heartbeat_event import (
    NODE_HEARTBEAT_EVENT,
    ModelNodeHeartbeatEvent,
)

__all__ = [
    # Event type constants
    "CONTRACT_DEREGISTERED_EVENT",
    "CONTRACT_REGISTERED_EVENT",
    "NODE_HEARTBEAT_EVENT",
    # Event models
    "ModelContractDeregisteredEvent",
    "ModelContractRegisteredEvent",
    "ModelNodeHeartbeatEvent",
]
