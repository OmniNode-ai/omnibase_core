# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Root delegation runtime profile contract model for OMN-10919.

Typed Pydantic v2 schema for the delegation runtime configuration surface.
Frozen + extra=forbid — pure schema with no env var reads or I/O.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_delegation_dashboard_connection import (
    ModelDelegationDashboardConnection,
)
from omnibase_core.models.contracts.model_delegation_datastore import (
    ModelDelegationDatastore,
)
from omnibase_core.models.contracts.model_delegation_event_bus_endpoint import (
    ModelDelegationEventBusEndpoint,
)
from omnibase_core.models.contracts.model_delegation_llm_backend import (
    ModelDelegationLlmBackend,
)
from omnibase_core.models.contracts.model_delegation_pricing_manifest_ref import (
    ModelDelegationPricingManifestRef,
)
from omnibase_core.models.contracts.model_delegation_security import (
    ModelDelegationSecurity,
)


class ModelDelegationRuntimeProfile(BaseModel):
    """Root contract for delegation runtime profile configuration.

    Defines all runtime dependencies for the delegation routing pipeline:
    event bus, LLM backends, security, pricing, dashboard, and datastores.
    All values are typed references — no raw secrets, no hardcoded endpoints.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., description="Human-readable profile name")
    version: int = Field(..., ge=1, description="Profile version; must be >= 1")
    runtime_profile: str = Field(
        ...,
        description="Runtime environment identifier (e.g. local, staging, production)",
    )
    event_bus: ModelDelegationEventBusEndpoint = Field(
        ...,
        description="Event bus endpoint configuration",
    )
    llm_backends: dict[str, ModelDelegationLlmBackend] = Field(
        ...,
        description="Named LLM backend configurations (at least 'default' expected)",
    )
    security: ModelDelegationSecurity | None = Field(
        default=None,
        description="Optional security configuration",
    )
    pricing: ModelDelegationPricingManifestRef | None = Field(
        default=None,
        description="Optional pricing manifest reference",
    )
    dashboard: ModelDelegationDashboardConnection | None = Field(
        default=None,
        description="Optional dashboard connection configuration",
    )
    datastores: dict[str, ModelDelegationDatastore] | None = Field(
        default=None,
        description="Optional named datastore configurations",
    )
