# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Capabilities models for ONEX nodes.

This package provides models for node capabilities and contract-derived
capabilities to enable capability-based auto-discovery and registration.

Modules:
    model_contract_capabilities: Contract-derived capabilities for auto-discovery.
    model_capability_metadata: Capability metadata for documentation/discovery.

Usage:
    from omnibase_core.models.capabilities import (
        ModelContractCapabilities,
        ModelCapabilityMetadata,
    )
    from omnibase_core.models.primitives.model_semver import ModelSemVer

    # Contract-derived capabilities for runtime registration
    capabilities = ModelContractCapabilities(
        contract_type="compute",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        intent_types=["ProcessData"],
        protocols=["ProtocolCompute"],
        capability_tags=["pure", "cacheable"],
    )

    # Capability metadata for documentation/discovery
    metadata = ModelCapabilityMetadata(
        capability="database.relational",
        name="Relational Database",
        version=ModelSemVer(major=1, minor=0, patch=0),
        description="SQL-based relational database operations",
        tags=("storage", "sql"),
        required_features=("query", "transactions"),
    )

OMN-1124: Capabilities models package.
OMN-1156: ModelCapabilityMetadata for documentation/discovery.
"""

from omnibase_core.models.capabilities.model_capability_metadata import (
    ModelCapabilityMetadata,
)
from omnibase_core.models.capabilities.model_contract_capabilities import (
    ModelContractCapabilities,
)

__all__ = [
    "ModelCapabilityMetadata",
    "ModelContractCapabilities",
]
