# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodEvidenceItem — a single DoD evidence entry for a Linear ticket. OMN-8916

OMN-9787 — `file_exists` is structurally weak proof. A `dod_evidence` item
whose only declared `check_type` is `file_exists` is a tautology when the
recorded path points at the receipt file itself: the receipt becomes its own
evidence. The contract-side validator below rejects that shape so the
anti-pattern cannot be encoded in any new contract.

The validator is pure (no I/O); legacy-contract allowlist / exemption logic
lives in the gate (Task 8 / `check_dod_compliance.py`), keyed on the stable
machine token ``DOD_EVIDENCE_FILE_EXISTS_SOLE_CHECK`` carried in the raised
``ValueError``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)

# Machine-readable token raised when the sole-`file_exists` rule trips. The
# Task 8 gate keys allowlist exemption decisions on this token, so it must
# not drift. Listed here (not buried in the validator body) so the contract
# is grep-able from the gate side.
SOLE_FILE_EXISTS_ERROR_TOKEN = "DOD_EVIDENCE_FILE_EXISTS_SOLE_CHECK"  # env-var-ok: constant definition  # noqa: secrets

# `file_exists` is structurally weak: file presence proves a write occurred,
# not that the behavior under test ran. Pairing it with at least one stronger
# check_type (command, test_passes, endpoint, grep, test_exists) rescues the
# evidence item.
_WEAK_PROOF_CHECK_TYPES = frozenset({"file_exists"})


class ModelDodEvidenceItem(BaseModel):
    """A single DoD evidence entry declaring what must be verified before Done."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    checks: list[ModelDodEvidenceCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_sole_file_exists_check(self) -> ModelDodEvidenceItem:
        """Reject evidence items where the only declared check is `file_exists`.

        Rationale: a `file_exists` check pointing at the receipt file itself is
        tautological — the receipt becomes its own evidence. Even when the path
        targets some other file, presence proves a write, not that the behavior
        under test executed. To prevent this anti-pattern at the contract layer,
        items whose ``check_type`` set is exactly ``{"file_exists"}`` are
        rejected. Pair with at least one of: command, test_passes, endpoint,
        grep, test_exists.

        Items with no checks declared at all are not flagged here — that case
        is handled at the parent-contract level (``dod_evidence`` requires
        ``min_length=1``); this validator only flags the specific tautology
        shape so the error surface stays narrow and grep-able.
        """
        if not self.checks:
            return self
        types_present = {check.check_type for check in self.checks}
        if types_present.issubset(_WEAK_PROOF_CHECK_TYPES):
            msg = (
                f"{SOLE_FILE_EXISTS_ERROR_TOKEN}: file_exists is weak proof and "
                "cannot be the sole check_type for a dod_evidence item. The "
                "receipt file pointing at itself is tautological — the receipt "
                "becomes its own evidence. Pair file_exists with at least one "
                "of: command, test_passes, endpoint, grep, test_exists."
            )
            raise ValueError(msg)
        return self


__all__ = ["SOLE_FILE_EXISTS_ERROR_TOKEN", "ModelDodEvidenceItem"]
