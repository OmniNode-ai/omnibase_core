# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DoD Sweep Check Types.

The 6 per-ticket checks performed during a DoD compliance sweep,
organized into two confidence tiers (primary artifact checks and
supporting operational checks).
"""

from enum import Enum, unique


@unique
class EnumDodSweepCheck(str, Enum):
    """The 6 hard-fail checks performed per ticket during a DoD sweep.

    Checks are organized into two confidence tiers:
    - Primary (artifact checks): CONTRACT_EXISTS, RECEIPT_EXISTS, RECEIPT_CLEAN
      High confidence -- deterministic file existence + content parsing.
    - Supporting (operational checks): PR_MERGED, CI_GREEN, INTEGRATION_SWEEP_EVIDENCE
      Medium confidence -- depends on cross-repo search and SHA linkage.
      Should record UNKNOWN (not FAIL) when linkage cannot be established.
    """

    CONTRACT_EXISTS = "contract_exists"
    """Ticket contract YAML exists in contracts/ directory."""

    RECEIPT_EXISTS = "receipt_exists"
    """DoD evidence receipt exists in .evidence/{ticket_id}/ directory."""

    RECEIPT_CLEAN = "receipt_clean"
    """DoD evidence receipt has zero failures."""

    PR_MERGED = "pr_merged"
    """At least one PR matching the ticket ID has been merged."""

    CI_GREEN = "ci_green"
    """CI checks on the merge commit all passed."""

    INTEGRATION_SWEEP_EVIDENCE = "integration_sweep_evidence"
    """Integration sweep evidence linked to the ticket exists."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
