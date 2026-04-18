# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumReceiptStatus — outcome of a dod_evidence check run."""

from __future__ import annotations

from enum import StrEnum


class EnumReceiptStatus(StrEnum):
    """Terminal status of a dod_evidence check execution.

    Used by `ModelDodReceipt` to declare whether the check proved the
    claim it was supposed to prove. Only PASS receipts satisfy the
    receipt-gate CI check; FAIL and any missing receipt both block merge.
    """

    PASS = "PASS"
    FAIL = "FAIL"


__all__ = ["EnumReceiptStatus"]
