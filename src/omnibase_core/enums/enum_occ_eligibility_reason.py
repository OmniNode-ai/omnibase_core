# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OCC merge eligibility failure reasons."""

from __future__ import annotations

from enum import StrEnum


class EnumOccEligibilityReason(StrEnum):
    """Standardized reason values emitted by the OCC eligibility gate."""

    ELIGIBLE = "eligible"
    MISSING_TICKET = "missing_ticket"
    MISSING_CONTRACT = "missing_contract"
    MISSING_RECEIPT = "missing_receipt"
    NONPASS_RECEIPT = "nonpass_receipt"
    CONTRACT_HASH_MISMATCH = "contract_hash_mismatch"
    OCC_NOT_ON_MAIN = "occ_not_on_main"
    PR_TICKET_MISMATCH = "pr_ticket_mismatch"
    # OMN-16353: the missing-self-bind-ONLY case on the OCC evidence repo —
    # contracts resolve, receipts are PASS and hash-bound, but no receipt binds
    # to the OCC PR itself (`occ-self-bind-pr-<N>` omitted). Split out of
    # PR_TICKET_MISMATCH so the gate can name the exact remedy.
    MISSING_OCC_SELF_BIND = "missing_occ_self_bind"
    # OMN-16859: the receipt resolves, is hash-bound and PR-bound, and honestly
    # declares PENDING — the probe was allocated but has not executed yet —
    # on a check type a product-repo CI runner executes and supersedes.
    #
    # This is a LEGIBILITY split out of NONPASS_RECEIPT, never a relaxation:
    # the verdict stays `eligible=False`, and the gate reports it only when it
    # is the SOLE remaining blocker, so a genuinely missing or genuinely
    # FAILING receipt still wins. Exhaustive consumers should treat unknown
    # reasons as ineligible and may map this value to NONPASS_RECEIPT until
    # they render the more specific "wait for or fix the product-repo runner"
    # remedy. It exists because the OCC producers run in the .201 effects
    # runtime with no product checkout and structurally cannot execute a
    # `test_passes` check, so "non-PASS" pointed four separate lanes at the
    # wrong remedy (hand-author a receipt) on 2026-08-28 alone.
    AWAITING_RUNNER_RECEIPT = "awaiting_runner_receipt"
    # OR.2: goal-mode failures retain explicit source/subject reasons rather
    # than collapsing into ticket/body mismatch or timeout-like outcomes.
    GOAL_CONTRACT_INVALID = "goal_contract_invalid"
    CONTRACT_FORMAT_INVALID = "contract_format_invalid"
    GOAL_SUBJECT_MISMATCH = "goal_subject_mismatch"
    GOAL_ADMISSION_UNAVAILABLE = "goal_admission_unavailable"
    GOAL_ADMISSION_INCOMPLETE = "goal_admission_incomplete"
    GOAL_ATTEMPT_NONPASS = "goal_attempt_nonpass"
    GOAL_DEADLINE_EXPIRED = "goal_deadline_expired"
    GOAL_MUTATION_PENDING = "goal_mutation_pending"
    GOAL_ATTESTATION_INVALID = "goal_attestation_invalid"
    GOAL_CRITERION_COVERAGE_MISSING = "goal_criterion_coverage_missing"
    GOAL_CRITERION_BASELINE_MISMATCH = "goal_criterion_baseline_mismatch"
    GOAL_REVISION_HISTORY_INVALID = "goal_revision_history_invalid"
    GOAL_REVISION_FORK_UNRESOLVED = "goal_revision_fork_unresolved"
    GOAL_REVISION_NOT_CURRENT = "goal_revision_not_current"

    def legacy_external_value(self) -> str:
        """Return the v0.46-compatible reason value for exhaustive consumers."""
        if self is EnumOccEligibilityReason.AWAITING_RUNNER_RECEIPT:
            return EnumOccEligibilityReason.NONPASS_RECEIPT.value
        return self.value


__all__ = ["EnumOccEligibilityReason"]
