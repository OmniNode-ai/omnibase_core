# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolution tier enum for tiered authenticated dependency resolution.

Defines the trust boundary tiers through which resolution escalates.
Resolution progresses from local exact matches through organization-trusted
and federated-trusted providers, with quarantine as the final fallback.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumResolutionTier"]


@unique
class EnumResolutionTier(StrValueHelper, str, Enum):
    """Trust boundary tier for tiered dependency resolution.

    Resolution escalates through tiers in order, each requiring progressively
    stronger authentication proofs. The resolver tries each tier in sequence
    and returns the first successful match.

    Tier order: LOCAL_EXACT -> LOCAL_COMPATIBLE -> ORG_TRUSTED ->
    FEDERATED_TRUSTED -> QUARANTINE.
    """

    LOCAL_EXACT = "local_exact"
    """Exact match within the local trust domain. No additional proofs required."""

    LOCAL_COMPATIBLE = "local_compatible"
    """Compatible match within the local trust domain. Version flexibility allowed."""

    ORG_TRUSTED = "org_trusted"
    """Match from an organization-level trusted domain. Requires org membership proof."""

    FEDERATED_TRUSTED = "federated_trusted"
    """Match from a federated partner domain. Requires capability attestation."""

    QUARANTINE = "quarantine"
    """Untrusted match requiring full isolation and restricted capabilities."""
