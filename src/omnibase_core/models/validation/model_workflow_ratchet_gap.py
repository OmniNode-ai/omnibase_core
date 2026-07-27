# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pull-request-workflow count-locked-ratchet gap model (OMN-14907 / plan C7).

Represents a single gap between the count-locked ratchet registry
(``architecture-handshakes/pull-request-workflow-budget.yaml``) and the live set
of ``.github/workflows/*.yml`` files that trigger on ``pull_request`` /
``pull_request_target``.

Each gap carries a machine-readable ``code`` so a caller (CLI, CI job, pytest) can
branch on the failure class without string-matching the human ``detail``.

Related ticket: OMN-14907 (C7 count-locked workflow-file ratchet).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ModelWorkflowRatchetGap", "WORKFLOW_RATCHET_GAP_CODES"]

# The closed set of failure classes the ratchet can report. Kept as a module
# constant (not an Enum) to stay import-cheap for the pre-commit / CI CLI path,
# mirroring ModelNoncanonicalClassFinding (OMN-14350). Every value is asserted
# reachable by the planted-failure tests.
WORKFLOW_RATCHET_GAP_CODES: frozenset[str] = frozenset(
    {
        "UNREGISTERED",  # live PR-triggered workflow absent from allowlist and waivers
        "STALE",  # registry entry with no matching live file (retired without down-ratchet)
        "NOT_PR_TRIGGERED",  # allowlisted file no longer triggers on pull_request
        "BUDGET_MISMATCH",  # len(allowlist) != declared budget (silent registration growth)
        "WAIVER_EXPIRED",  # waiver past its expires date
        "WAIVER_INCOMPLETE",  # waiver missing a required field
    }
)


@dataclass(frozen=True, slots=True)
class ModelWorkflowRatchetGap:
    """A single pull-request-workflow count-locked-ratchet gap.

    ``workflow_file`` is the ``.github/workflows/*.yml`` file (or the registry
    key, for a budget-level gap) the finding concerns. ``code`` is one of
    :data:`WORKFLOW_RATCHET_GAP_CODES`. ``detail`` is human-readable.
    """

    workflow_file: str
    code: str
    detail: str

    def format(self) -> str:
        return f"  {self.workflow_file} [{self.code}] — {self.detail}"
