# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unified Node Introspection Event Model.

ModelNodeIntrospectionEvent for node introspection broadcasts
in the ONEX registration and discovery patterns.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumIntrospectionReason, EnumNodeKind
from omnibase_core.models.capabilities import ModelContractCapabilities
from omnibase_core.models.core.model_feature_flags import ModelFeatureFlags
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.registration.model_discovered_capabilities import (
    ModelDiscoveredCapabilities,
)
from omnibase_core.models.registration.model_introspection_performance_metrics import (
    ModelIntrospectionPerformanceMetrics,
)
from omnibase_core.models.registration.model_node_capabilities import (
    ModelNodeCapabilities,
)
from omnibase_core.models.registration.model_node_event_bus_config import (
    ModelNodeEventBusConfig,
)
from omnibase_core.models.registration.model_node_metadata import ModelNodeMetadata
from omnibase_core.utils.util_validators import (
    ensure_timezone_aware,
    validate_endpoint_urls_dict,
)


class ModelNodeIntrospectionEvent(BaseModel):
    """Unified event model for node introspection broadcasts.

    Nodes publish this event to announce their presence, capabilities,
    and endpoints to the cluster. Used by the Registry node to maintain
    a live catalog of available nodes and by introspection for service discovery.

    This model co-locates both declared capabilities (from contract) and
    discovered capabilities (from reflection) - they are NOT unified as they
    represent fundamentally different data.

    Attributes:
        node_id: Unique node identifier.
        node_type: ONEX node type (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR).
        node_version: Semantic version of the node.
        declared_capabilities: Contract-declared capabilities (feature flags).
        discovered_capabilities: Runtime-discovered capabilities (reflection).
        contract_capabilities: Contract-derived capabilities (design-time truth).
            Populated from the node's contract when available, None otherwise.
        endpoints: Dictionary of exposed endpoints (name -> URL).
        current_state: Current FSM state if the node has state management.
        reason: Why this introspection event was emitted.
        correlation_id: Required correlation ID for tracing and idempotency.
        timestamp: Event timestamp (must be timezone-aware).
        node_role: Optional role descriptor (registry, adapter, etc).
        metadata: Additional node metadata.
        network_id: Network/cluster identifier.
        deployment_id: Deployment/release identifier.
        epoch: Registration epoch for ordering.
        performance_metrics: Optional metrics from introspection operation.
        event_bus: Resolved event bus topic configuration for registry-driven routing.
            If None, node is NOT included in dynamic topic routing lookups.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import datetime, timezone
        >>> from omnibase_core.enums import EnumNodeKind
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> event = ModelNodeIntrospectionEvent(
        ...     node_id=uuid4(),
        ...     node_type=EnumNodeKind.EFFECT,
        ...     node_version=ModelSemVer(major=1, minor=2, patch=3),
        ...     correlation_id=uuid4(),
        ...     timestamp=datetime.now(timezone.utc),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # Core identity (required, strongly typed)
    node_id: UUID = Field(..., description="Unique node identifier")
    node_name: str | None = Field(
        default=None,
        description="Human-readable node name from contract metadata or snake_case class name. "
        "None only as degraded fallback — UUID fallback in e2e is a regression.",
    )
    node_type: EnumNodeKind = Field(..., description="ONEX node type")
    node_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Semantic version of the node",
    )

    # Co-located capabilities (different purposes, different structures)
    declared_capabilities: ModelNodeCapabilities = Field(
        default_factory=ModelNodeCapabilities,
        description="Node-declared capabilities from contract (feature flags)",
    )
    discovered_capabilities: ModelDiscoveredCapabilities = Field(
        default_factory=ModelDiscoveredCapabilities,
        description="Capabilities discovered via runtime reflection",
    )
    contract_capabilities: ModelContractCapabilities | None = Field(
        default=None,
        description="Contract-derived capabilities (design-time truth, deterministic). "
        "Populated by ContractCapabilityExtractor from the node's contract. "
        "None when contract is not available or extraction fails.",
    )

    # Endpoints and state
    endpoints: dict[str, str] = Field(
        default_factory=dict,
        description="Exposed endpoints (name -> URL)",
    )

    @field_validator("endpoints")
    @classmethod
    def validate_endpoint_urls(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate that all endpoint values are valid URLs.

        Delegates to shared utility for consistent validation across all models.
        """
        return validate_endpoint_urls_dict(v)

    current_state: str | None = Field(
        default=None,
        description="Current FSM state if node has state management",
    )

    # Event metadata (strongly typed)
    reason: EnumIntrospectionReason = Field(
        default=EnumIntrospectionReason.STARTUP,
        description="Why this introspection event was emitted",
    )
    correlation_id: UUID = Field(
        ...,
        description="Request correlation ID for tracing (required for idempotency)",
    )
    timestamp: datetime = Field(
        ...,
        description="Event timestamp (must be timezone-aware)",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_timezone_aware(cls, v: datetime) -> datetime:
        """Validate that timestamp is timezone-aware.

        Delegates to the shared core utility for consistent validation.
        """
        return ensure_timezone_aware(v, "timestamp")

    # Optional registration fields
    node_role: str | None = Field(
        default=None,
        description="Node role (registry, adapter, etc)",
    )
    metadata: ModelNodeMetadata = Field(
        default_factory=ModelNodeMetadata,
        description="Additional node metadata",
    )
    network_id: str | None = Field(
        default=None,
        description="Network/cluster identifier",
    )
    deployment_id: str | None = Field(
        default=None,
        description="Deployment/release identifier",
    )
    epoch: int | None = Field(
        default=None,
        ge=0,
        description="Registration epoch for ordering (monotonically increasing)",
    )

    # Optional discovery fields
    performance_metrics: ModelIntrospectionPerformanceMetrics | None = Field(
        default=None,
        description="Performance metrics from introspection operation",
    )
    event_bus: ModelNodeEventBusConfig | None = Field(
        default=None,
        description="Resolved event bus topic configuration. "
        "Contains environment-qualified topic strings for registry-driven routing. "
        "If None, node is NOT included in dynamic topic routing lookups.",
    )

    # Feature flags
    resolved_feature_flags: ModelFeatureFlags = Field(
        default_factory=ModelFeatureFlags,
        description="Feature flag values after applying env/control-plane overrides. "
        "Contrast with declared_capabilities.feature_flags which holds contract defaults only.",
    )


__all__ = ["ModelNodeIntrospectionEvent"]
