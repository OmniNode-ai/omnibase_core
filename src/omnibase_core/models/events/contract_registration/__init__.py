# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract registration event models.

Event models for dynamic contract discovery via Kafka (OMN-1651).
These events enable nodes to register/deregister contracts at runtime
and provide liveness heartbeats.

Models:
    ModelContractRegisteredEvent: Contract registration with full YAML for replay.
    ModelContractDeregisteredEvent: Graceful contract deregistration.
    ModelNodeHeartbeatEvent: Node liveness heartbeat.

Event Type Constants:
    CONTRACT_REGISTERED_EVENT: see TOPIC_CONTRACT_REGISTERED_EVENT in constants_event_types
    CONTRACT_DEREGISTERED_EVENT: see TOPIC_CONTRACT_DEREGISTERED_EVENT in constants_event_types
    NODE_HEARTBEAT_EVENT: see TOPIC_NODE_HEARTBEAT_EVENT in constants_event_types
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
