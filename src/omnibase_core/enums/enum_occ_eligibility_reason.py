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


__all__ = ["EnumOccEligibilityReason"]
