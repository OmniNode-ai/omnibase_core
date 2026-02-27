# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolution failure code enum for tiered authenticated dependency resolution.

Structured failure codes for when tiered resolution cannot satisfy a
dependency request. Each code identifies a specific class of resolution
failure for diagnostics and policy enforcement.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumResolutionFailureCode"]


@unique
class EnumResolutionFailureCode(StrValueHelper, str, Enum):
    """Structured failure code for tiered dependency resolution.

    When resolution fails, one of these codes is attached to the failure
    result to identify the root cause. Codes are ordered from most common
    (no providers found) to most specific (SLA not met).
    """

    NO_MATCH = "no_match"
    """No provider found matching the requested capability at the attempted tier."""

    MATCH_INSUFFICIENT_TRUST = "match_insufficient_trust"
    """Provider found but its trust level is below the required tier."""

    POLICY_DENIED = "policy_denied"
    """Resolution blocked by a classification gate or policy bundle rule."""

    KEY_MISMATCH = "key_mismatch"
    """Provider's signing key does not match the expected trust root."""

    ATTESTATION_INVALID = "attestation_invalid"
    """Capability attestation token is expired, malformed, or signature invalid."""

    SLA_NOT_MET = "sla_not_met"
    """Provider meets trust requirements but fails SLA constraints (latency, etc.)."""

    TIER_EXHAUSTED = "tier_exhausted"
    """All configured tiers attempted without successful resolution."""
