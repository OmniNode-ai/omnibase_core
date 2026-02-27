# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Proof type enum for capability attestation verification.

Defines the types of proofs that can be required and verified during
tiered dependency resolution. Each proof type corresponds to a specific
trust assertion that must be validated before resolution proceeds.

.. versionadded:: 0.21.0
    Phase 3 of authenticated dependency resolution (OMN-2892).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumProofType"]


@unique
class EnumProofType(StrValueHelper, str, Enum):
    """Type of proof required or verified during tiered resolution.

    Proofs are assertions about a node's identity, capabilities, or
    organizational membership that must be cryptographically verified
    before resolution at a given trust tier proceeds.
    """

    NODE_IDENTITY = "node_identity"
    """Proof that the subject node is who it claims to be (key-based identity)."""

    CAPABILITY_ATTESTED = "capability_attested"
    """Proof that a trusted issuer has attested the node's capability claim."""

    ORG_MEMBERSHIP = "org_membership"
    """Proof that the node belongs to the claimed organization domain."""

    BUS_MEMBERSHIP = "bus_membership"
    """Proof that the node is authorized to participate on a specific event bus."""

    POLICY_COMPLIANCE = "policy_compliance"
    """Proof that the node's configuration complies with the active policy bundle."""
