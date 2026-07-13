# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Registration domain models for ONEX node registration workflows.

Pure data models for node registration operations.
These models follow the ONEX "Intent -> Effect" pattern where Reducers
compute registration payloads deterministically, and Effects perform
actual registration operations.

Models:
    ModelRegistrationPayload:
        Typed payload for registration intents. Contains all information
        needed to register a node to PostgreSQL. Emitted by Reducers,
        consumed by Effects.

    ModelDualRegistrationOutcome:
        Domain-level outcome of registration. Captures the result
        of registering to PostgreSQL. Returned by Effects,
        aggregated by Orchestrators.

Design Principles:
    - **Pure Domain Models**: No I/O dependencies, no infrastructure concerns
    - **Immutable**: All models are frozen (thread-safe after creation)
    - **Typed**: Strong typing with validation constraints
    - **Serializable**: Full JSON serialization support

Data Flow:
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                  Registration Workflow Flow                       │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   Introspection   Reducer            Effect        Orchestrator  │
    │        │             │                  │               │        │
    │        │  process    │                  │               │        │
    │        │────────────>│                  │               │        │
    │        │             │  Payload         │               │        │
    │        │             │─────────────────>│               │        │
    │        │             │                  │   Outcome     │        │
    │        │             │                  │──────────────>│        │
    │        │             │                  │               │ agg    │
    │                                                                  │
    └──────────────────────────────────────────────────────────────────┘
    ```

Usage:
    >>> from omnibase_core.models.registration import (
    ...     ModelRegistrationPayload,
    ...     ModelDualRegistrationOutcome,
    ... )
    >>> from uuid import uuid4
    >>> from pydantic import BaseModel
    >>>
    >>> # Create a registration payload
    >>> class NodeRecord(BaseModel):
    ...     node_id: str
    ...     status: str
    >>>
    >>> payload = ModelRegistrationPayload(
    ...     node_id=uuid4(),
    ...     deployment_id=uuid4(),
    ...     environment="production",
    ...     network_id="vpc-main",
    ...     postgres_record=NodeRecord(node_id="123", status="active"),
    ... )
    >>>
    >>> # Create a registration outcome
    >>> outcome = ModelDualRegistrationOutcome(
    ...     node_id=uuid4(),
    ...     status="success",
    ...     postgres_applied=True,
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.intents: Core infrastructure intents
    omnibase_core.models.reducer.model_intent: Extension intents
    omnibase_core.nodes.NodeReducer: Emits registration payloads
    omnibase_core.nodes.NodeEffect: Consumes payloads, returns outcomes
    omnibase_core.nodes.NodeOrchestrator: Aggregates outcomes
"""

from omnibase_core.models.registration.model_discovered_capabilities import (
    ModelDiscoveredCapabilities,
)
from omnibase_core.models.registration.model_dual_registration_outcome import (
    ModelDualRegistrationOutcome,
)
from omnibase_core.models.registration.model_event_bus_topic_entry import (
    ModelEventBusTopicEntry,
)
from omnibase_core.models.registration.model_introspection_performance_metrics import (
    ModelIntrospectionPerformanceMetrics,
)
from omnibase_core.models.registration.model_mcp_contract_config import (
    ModelMCPContractConfig,
)
from omnibase_core.models.registration.model_node_capabilities import (
    ModelNodeCapabilities,
)
from omnibase_core.models.registration.model_node_event_bus_config import (
    ModelNodeEventBusConfig,
)
from omnibase_core.models.registration.model_node_introspection_event import (
    ModelNodeIntrospectionEvent,
)
from omnibase_core.models.registration.model_node_metadata import ModelNodeMetadata
from omnibase_core.models.registration.model_registration_payload import (
    ModelRegistrationPayload,
)

__all__ = [
    # Registration workflow payloads
    "ModelRegistrationPayload",
    "ModelDualRegistrationOutcome",
    # Node introspection wire event + nested DTOs
    # (OMN-14490 — graduated from omnibase_infra as the single canonical home)
    "ModelNodeIntrospectionEvent",
    "ModelDiscoveredCapabilities",
    "ModelEventBusTopicEntry",
    "ModelIntrospectionPerformanceMetrics",
    "ModelMCPContractConfig",
    "ModelNodeCapabilities",
    "ModelNodeEventBusConfig",
    "ModelNodeMetadata",
]
