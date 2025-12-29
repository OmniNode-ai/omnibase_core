# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Capabilities models for ONEX nodes.

This package provides models for node capabilities and contract-derived
capabilities to enable capability-based auto-discovery and registration.

Modules:
    model_contract_capabilities: Contract-derived capabilities for auto-discovery.

Usage:
    from omnibase_core.models.capabilities import ModelContractCapabilities

    capabilities = ModelContractCapabilities(
        contract_type="compute",
        contract_version="1.0.0",
        intent_types=["ProcessData"],
        protocols=["ProtocolCompute"],
        capability_tags=["pure", "cacheable"],
    )

OMN-1124: Capabilities models package.
"""

from omnibase_core.models.capabilities.model_contract_capabilities import (
    ModelContractCapabilities,
)

__all__ = [
    "ModelContractCapabilities",
]
