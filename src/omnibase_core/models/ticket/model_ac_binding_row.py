# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One row of the acceptance-criterion / evidence-check binding table.

OMN-18056. The closer's flip predicate counted checks and never asked which
criterion any of them covered. Counters can refute "every criterion is
covered by a verified probative check"; they cannot say WHICH criterion is
not covered, and on the nine tickets adjudicated in closeout sweep run 2 the
criterion that decided the ticket was, in every held case, bound to no check
at all.

A row is the join the counters could not express: one acceptance criterion,
and one evidence check that DECLARES it (``binds_ac`` on the contract's
evidence item, surfaced per check on the dod_verify verdict). A criterion no
check declares gets exactly one row with an empty ``evidence_check`` — the absence
is a fact the record has to state, not one it may omit, because an AC with no
row is indistinguishable from an AC nobody parsed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_ac_binding_check_status import (
    EnumAcBindingCheckStatus,
)


class ModelAcBindingRow(BaseModel):
    """One (acceptance criterion, declaring check) pair, or an unbound criterion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    acceptance_criterion: str = Field(
        ...,
        min_length=1,
        description=(
            "The criterion as it appears in the ticket body, bounded in "
            "length for rendering. Verbatim so a reader can find it."
        ),
    )
    label: str = Field(
        default="",
        description=(
            "Canonical label parsed from the criterion (`AC3`, `DOD2`). Empty "
            "when the criterion carries no label — which is itself why it "
            "cannot be bound: `binds_ac` has nothing to point at."
        ),
    )
    evidence_check: str = Field(
        default="",
        description=(
            "`evidence_id` of the check declaring this criterion -- a contract "
            "author's label such as `dod-tests`, never a uuid. Empty on the "
            "single row that records an UNBOUND criterion."
        ),
    )
    status: EnumAcBindingCheckStatus = Field(
        default=EnumAcBindingCheckStatus.UNKNOWN,
        description=(
            "That check's dod_verify status. Only VERIFIED binds; the others "
            "are recorded so a declared-but-unproven binding is visible in "
            "the table rather than silently absent."
        ),
    )
    proof_class: str = Field(
        default="",
        description="That check's proof class (`behavior`, `merge-state`, ...).",
    )
    bound: bool = Field(
        default=False,
        description=(
            "True only when this row is a VERIFIED check declaring this "
            "criterion — the one shape that discharges it."
        ),
    )


__all__ = ["ModelAcBindingRow"]
