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

    def legacy_external_value(self) -> str:
        """Return the v0.46-compatible reason value for exhaustive consumers."""
        if self is EnumOccEligibilityReason.AWAITING_RUNNER_RECEIPT:
            return EnumOccEligibilityReason.NONPASS_RECEIPT.value
        return self.value


__all__ = ["EnumOccEligibilityReason"]
