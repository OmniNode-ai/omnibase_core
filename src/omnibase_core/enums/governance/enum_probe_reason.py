# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe Reason Enum.

Reason codes for UNKNOWN or SKIPPED probe results in integration sweeps.
"""

from enum import Enum, unique


@unique
class EnumProbeReason(str, Enum):
    """Reason codes explaining why a probe result is UNKNOWN or SKIPPED.

    Used by ModelIntegrationRecord to communicate why a probe could not
    produce a definitive PASS/FAIL result:
    - NO_CONTRACT: No ticket contract exists for this integration point
    - PROBE_UNAVAILABLE: The probe skill is not available in this environment
    - INCONCLUSIVE: Probe ran but could not determine a definitive result
    - NOT_APPLICABLE: The probe category does not apply to this artifact
    """

    NO_CONTRACT = "no_contract"
    """No ticket contract exists for this integration point."""

    PROBE_UNAVAILABLE = "probe_unavailable"
    """The probe skill is not available in this environment."""

    INCONCLUSIVE = "inconclusive"
    """Probe ran but could not determine a definitive result."""

    NOT_APPLICABLE = "not_applicable"
    """The probe category does not apply to this artifact."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
