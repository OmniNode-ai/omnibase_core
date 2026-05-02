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


__all__ = ["EnumOccEligibilityReason"]
