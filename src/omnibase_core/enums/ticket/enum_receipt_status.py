# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumReceiptStatus — outcome of a dod_evidence check run."""

from __future__ import annotations

from enum import StrEnum


class EnumReceiptStatus(StrEnum):
    """Terminal status of a dod_evidence check execution.

    Used by :class:`ModelDodReceipt` to declare whether the check proved the
    claim it was supposed to prove. Only ``PASS`` receipts satisfy the
    receipt-gate CI check; ``FAIL`` and any missing receipt both block merge.

    Members
    -------
    PASS
        The probe executed and the observed result matched the claim.
        This is the only status that satisfies the receipt-gate.
    FAIL
        The probe executed and the observed result contradicted the claim.
        Treated identically to absence of a receipt — blocks merge.
    ADVISORY
        The probe executed but the proof is structurally weak. Set by the
        Centralized Transition Policy when (a) ``verifier == runner`` (the
        author self-attested) or (b) ``check_type == "file_exists"`` (the
        only proof is that a file was written, not that the underlying
        behavior was exercised). Advisory receipts are recorded for audit
        but do not satisfy the receipt-gate.
    PENDING
        The probe was allocated (e.g. by a pipeline that planned the run)
        but has not yet executed. Receipts in PENDING state never satisfy
        the receipt-gate; they exist so the absence of execution is
        explicit rather than inferred from missing files.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    ADVISORY = "ADVISORY"
    PENDING = "PENDING"


__all__ = ["EnumReceiptStatus"]
