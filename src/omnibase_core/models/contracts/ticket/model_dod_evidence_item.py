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

Note: the validator's user-facing error message advises *replacement* of
`file_exists` rather than pairing it with a stronger check_type. Pairing is
structurally permitted at the contract layer (legacy contracts can validate
during migration), but the runtime receipt gate
(``model_dod_receipt.py`` + ``receipt_gate.py``) downgrades every
`file_exists` receipt to ADVISORY and rejects non-PASS receipts, so paired
contracts still fail the gate at runtime. Only replacement actually
unblocks merge.
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
SOLE_FILE_EXISTS_ERROR_TOKEN = "DOD_EVIDENCE_FILE_EXISTS_SOLE_CHECK"  # env-var-ok: constant definition  # secret-ok: stable contract token

# `file_exists` is structurally weak: file presence proves a write occurred,
# not that the behavior under test ran. The contract layer rejects only the
# tautology shape (sole-`file_exists`); pairing with a stronger check_type
# is structurally permitted here so legacy contracts that mix shapes can
# still validate while being migrated. Note that the runtime receipt gate
# (``model_dod_receipt.py`` weak-proof rule + ``receipt_gate.py`` PASS
# requirement) downgrades every `file_exists` receipt to ADVISORY and then
# fails on any non-PASS receipt, so paired contracts still cannot merge —
# the only mergeable remediation is to replace `file_exists` with one of
# the stronger types (command, test_passes, endpoint, grep, test_exists).
_WEAK_PROOF_CHECK_TYPES = frozenset({"file_exists"})


class ModelDodEvidenceItem(BaseModel):
    """A single DoD evidence entry declaring what must be verified before Done."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    checks: list[ModelDodEvidenceCheck] = Field(default_factory=list)
    # OMN-18056. WHICH ACCEPTANCE CRITERIA THIS ITEM CLAIMS TO COVER.
    #
    # Until this field existed the relation between a ticket's acceptance
    # criteria and its evidence items was not merely undeclared, it was
    # UNDECLARABLE: ``extra="forbid"`` above meant a contract that tried to
    # state it would fail to parse. So the only question the evidence
    # autoclose sweep could ask of a green verdict was "how many checks
    # passed", never "which criterion did any of them cover".
    #
    # Measured (DoD closeout sweep run 2, 2026-09-08): 8 of 9 adjudicated
    # sprint tickets satisfied the closer's full flip predicate and 7 of those
    # 8 were not done — in every held case the acceptance criterion that
    # decides the ticket was bound to no check in its contract. A corpus grep
    # over all 8709 contracts for any binding field returned 0 files, against
    # a positive control of 8708 for ``dod_evidence``.
    #
    # OPTIONAL AND DEFAULTED, so all 8709 existing contracts keep parsing
    # unchanged; ``extra="forbid"`` stays, because forbidding what is not
    # declared is the property that made this field necessary rather than a
    # defect to route around.
    #
    # HONEST LIMIT, stated rather than implied: this is the AUTHOR'S CLAIM. A
    # consumer can verify that a named check ran and was probative; it cannot
    # verify that the check proves the criterion. What the field removes is
    # the SILENT case — a criterion nothing even claims to cover — not
    # authorial error.
    binds_ac: tuple[str, ...] = Field(
        default=(),
        description=(
            "Acceptance-criterion labels (`AC1`, `DoD2`) from the ticket body "
            "that this evidence item claims to prove. Empty means the item "
            "claims none, which is a coverage gap rather than a pass."
        ),
    )

    @model_validator(mode="after")
    def reject_sole_file_exists_check(self) -> ModelDodEvidenceItem:
        """Reject evidence items where the only declared check is `file_exists`.

        Rationale: a `file_exists` check pointing at the receipt file itself is
        tautological — the receipt becomes its own evidence. Even when the path
        targets some other file, presence proves a write, not that the behavior
        under test executed. To prevent this anti-pattern at the contract layer,
        items whose ``check_type`` set is exactly ``{"file_exists"}`` are
        rejected.

        The error message advises *replacement* rather than pairing: the
        runtime receipt gate downgrades every `file_exists` receipt to
        ADVISORY (see ``ModelDodReceipt`` weak-proof rule) and then fails on
        any non-PASS receipt (see ``receipt_gate.validate_pr_receipts``), so
        contracts that simply pair `file_exists` with a stronger check still
        fail the gate at runtime. Replacement is the only mergeable
        remediation; pairing is structurally permitted here only to keep
        legacy mixed-shape contracts validating during migration.

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
                "becomes its own evidence. Replace file_exists with one of: "
                "command, test_passes, endpoint, grep, test_exists. Pairing "
                "file_exists alongside a stronger check is permitted here but "
                "will not pass the runtime receipt gate, which downgrades every "
                "file_exists receipt to ADVISORY and rejects non-PASS receipts."
            )
            raise ValueError(msg)
        return self


__all__ = ["SOLE_FILE_EXISTS_ERROR_TOKEN", "ModelDodEvidenceItem"]
