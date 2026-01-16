"""Registration domain models for ONEX node registration workflows.

This module provides pure data models for node registration operations.
These models follow the ONEX "Intent -> Effect" pattern where Reducers
compute registration payloads deterministically, and Effects perform
actual registration operations.

Models:
    ModelRegistrationPayload:
        Typed payload for registration intents. Contains all information
        needed to register a node to both Consul and PostgreSQL. Emitted
        by Reducers, consumed by Effects.

    ModelDualRegistrationOutcome:
        Domain-level outcome of dual registration. Captures the result
        of registering to both Consul and PostgreSQL. Returned by Effects,
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
    ...     consul_service_id="node-123",
    ...     consul_service_name="onex-compute",
    ...     consul_tags=["env:prod"],
    ...     consul_health_check=None,
    ...     postgres_record=NodeRecord(node_id="123", status="active"),
    ... )
    >>>
    >>> # Create a registration outcome
    >>> outcome = ModelDualRegistrationOutcome(
    ...     node_id=uuid4(),
    ...     status="success",
    ...     postgres_applied=True,
    ...     consul_applied=True,
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.intents: Core infrastructure intents
    omnibase_core.models.reducer.model_intent: Extension intents
    omnibase_core.nodes.NodeReducer: Emits registration payloads
    omnibase_core.nodes.NodeEffect: Consumes payloads, returns outcomes
    omnibase_core.nodes.NodeOrchestrator: Aggregates outcomes
"""

from omnibase_core.models.registration.model_dual_registration_outcome import (
    ModelDualRegistrationOutcome,
)
from omnibase_core.models.registration.model_registration_payload import (
    ModelRegistrationPayload,
)

__all__ = [
    "ModelRegistrationPayload",
    "ModelDualRegistrationOutcome",
]
