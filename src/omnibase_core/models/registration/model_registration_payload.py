"""Typed payload for registration intents.

This module provides ModelRegistrationPayload, a pure data model that carries
all information needed to perform node registration. This model is emitted
by the Reducer as the payload of a ModelIntent and consumed by Effect nodes.

Design Pattern:
    ModelRegistrationPayload follows the ONEX "Intent -> Effect" pattern where:
    1. Reducer computes this payload deterministically from introspection events
    2. Payload is wrapped in a ModelIntent and emitted
    3. Effect node receives the payload and performs actual registration

    The payload contains ALL information needed for registration:
    - Node identity (node_id, deployment_id)
    - Environment context (environment, network_id)
    - Consul projection (service_id, name, tags, health_check)
    - PostgreSQL record (postgres_record)

    This separation ensures Reducer purity - the Reducer declares the desired
    registration state without performing actual I/O operations.

Data Flow:
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                   Registration Payload Flow                       │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   IntrospectionEvent     Reducer                 Effect          │
    │         │                   │                      │             │
    │         │   process         │                      │             │
    │         │──────────────────>│                      │             │
    │         │                   │   (state,            │             │
    │         │                   │    intents w/        │             │
    │         │                   │    payload)          │             │
    │         │                   │─────────────────────>│             │
    │         │                   │                      │ register    │
    │         │                   │                      │ to Consul   │
    │         │                   │                      │ + Postgres  │
    │                                                                  │
    └──────────────────────────────────────────────────────────────────┘
    ```

Thread Safety:
    ModelRegistrationPayload is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.registration import ModelRegistrationPayload
    >>> from omnibase_core.models.intents import ModelRegistrationRecordBase
    >>>
    >>> # Create a Postgres record
    >>> class NodeRecord(ModelRegistrationRecordBase):
    ...     node_id: str
    ...     node_type: str
    ...     status: str
    >>>
    >>> record = NodeRecord(node_id="node-123", node_type="compute", status="active")
    >>>
    >>> # Create registration payload
    >>> payload = ModelRegistrationPayload(
    ...     node_id=uuid4(),
    ...     deployment_id=uuid4(),
    ...     environment="production",
    ...     network_id="vpc-main",
    ...     consul_service_id="node-compute-123",
    ...     consul_service_name="onex-compute",
    ...     consul_tags=["node_type:compute", "env:production"],
    ...     consul_health_check={"http": "http://localhost:8080/health"},
    ...     postgres_record=record,
    ... )

See Also:
    omnibase_core.models.registration.ModelDualRegistrationOutcome: Outcome model
    omnibase_core.models.reducer.model_intent.ModelIntent: Extension intent wrapper
    omnibase_core.models.intents.ModelRegistrationRecordBase: Record base class
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.models.intents import ModelRegistrationRecordBase


class ModelRegistrationPayload(BaseModel):
    """Typed payload for registration intents.

    This model is emitted by the Reducer as the payload of a ModelIntent.
    It contains all information needed to perform registration, computed
    deterministically from the introspection event.

    This is a PURE data model with no I/O dependencies. Effect nodes
    consume this payload to perform actual Consul and PostgreSQL operations.

    Attributes:
        node_id: Unique identifier for the node being registered.
        deployment_id: Identifier for the deployment instance.
        environment: Deployment environment (e.g., "production", "staging").
        network_id: Network identifier for service discovery routing.
        consul_service_id: Service ID for Consul registration (deterministic).
        consul_service_name: Service name for Consul (e.g., "onex-compute").
        consul_tags: List of tags for Consul service metadata.
        consul_health_check: Optional health check configuration for Consul.
        postgres_record: The registration record to persist in PostgreSQL.

    Example:
        >>> from uuid import uuid4
        >>> from pydantic import BaseModel
        >>>
        >>> class SimpleRecord(BaseModel):
        ...     node_id: str
        ...     status: str
        >>>
        >>> payload = ModelRegistrationPayload(
        ...     node_id=uuid4(),
        ...     deployment_id=uuid4(),
        ...     environment="staging",
        ...     network_id="internal",
        ...     consul_service_id="svc-123",
        ...     consul_service_name="my-service",
        ...     consul_tags=["env:staging"],
        ...     consul_health_check=None,
        ...     postgres_record=SimpleRecord(node_id="123", status="active"),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Node Identity ----
    node_id: UUID = Field(
        ...,
        description="Unique identifier for the node being registered.",
    )
    deployment_id: UUID = Field(
        ...,
        description="Identifier for the deployment instance.",
    )

    # ---- Environment Context ----
    environment: str = Field(
        ...,
        description="Deployment environment (e.g., 'production', 'staging').",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )
    network_id: str = Field(
        ...,
        description="Network identifier for service discovery routing.",
        min_length=1,
        max_length=200,
    )

    # ---- Consul Projection (Deterministic) ----
    consul_service_id: str = Field(
        ...,
        description=(
            "Service ID for Consul registration. Deterministically computed "
            "from node_id and deployment context."
        ),
        min_length=1,
        max_length=200,
    )
    consul_service_name: str = Field(
        ...,
        description="Service name for Consul (e.g., 'onex-compute').",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )
    consul_tags: list[str] = Field(
        default_factory=list,
        description="List of tags for Consul service metadata.",
    )
    # ONEX_EXCLUDE: dict_str_any - Consul health check schema requires flexible types (booleans, integers, nested objects)
    consul_health_check: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional health check configuration for Consul. "
            "Supports full Consul health check schema including boolean fields "
            "(e.g., tls_skip_verify, TCPUseTLS), integer fields "
            "(e.g., SuccessBeforePassing), and nested objects/arrays "
            "(e.g., header, body)."
        ),
    )

    # ---- PostgreSQL Record (Source of Truth) ----
    postgres_record: ModelRegistrationRecordBase = Field(
        ...,
        description=(
            "The registration record to persist in PostgreSQL. "
            "This is the source of truth for node registration data."
        ),
    )


__all__ = ["ModelRegistrationPayload"]
