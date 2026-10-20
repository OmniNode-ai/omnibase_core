# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContractAcBindingRetirement — one binding a merged item withdraws.

OMN-21220. A merged ``dod_evidence`` item is never edited, so the only way to
withdraw a binding it makes is an entry appended on a later item:
``supersedes_ac_binding``. The DoD verifier (omnimarket ``node_dod_verify``)
reads it to retire a binding on a criterion the live ticket no longer carries,
which is the remedy its own CRITERIA_DRIFT verdict names.

Until now only onex_change_control's ``ModelDodEvidenceItem`` declared the
field. With OCC retired (OMN-20074), a product repository validates its
contracts against ``ModelTicketContract`` here, and that refused the entry as
an extra input, while the verifier refused it because no OCC tree held the
model that owns it. A product-repo contract therefore had no legal way to
retire a drifted binding. This model is that field's shape, carried over from
OCC unchanged so a contract written against either parses against both.

``reason_kind``, ``superseded_by``, ``retired_by`` and ``retired_at`` stay
optional so retirements already merged (item, label and reason only) still
parse; the verifier honours a retirement only when it carries the typed reason
and both audit fields.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.ticket.enum_ac_binding_retirement_reason import (
    EnumAcBindingRetirementReason,
)

# The label shape ``binds_ac`` and the binding records accept, with the
# optional single-letter suffix (``AC2b``) a split criterion carries.
_AC_LABEL_RE = re.compile(r"^(AC|DOD)[-_ .]?(\d+)([a-zA-Z]?)$", re.IGNORECASE)
_UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_MAX_ID_LENGTH = 50
_MAX_ACTOR_LENGTH = 200
_MAX_REASON_LENGTH = 2000
_MIN_REASON_LENGTH = 12


class ModelContractAcBindingRetirement(BaseModel):
    """One binding withdrawn: which item, which criterion, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    item: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_ID_LENGTH,
        description=(
            "The `dod_evidence` id whose binding is retired. It must be an item "
            "this same contract declares, and that item must bind the label."
        ),
    )
    label: str = Field(
        ...,
        max_length=50,
        description="The acceptance-criterion label unbound from that item.",
    )
    reason: str = Field(
        ...,
        min_length=_MIN_REASON_LENGTH,
        max_length=_MAX_REASON_LENGTH,
        description="Why this binding cannot settle this criterion.",
    )
    reason_kind: EnumAcBindingRetirementReason | None = Field(
        default=None,
        description=(
            "`superseded_by` (another item now binds the label, named in "
            "`superseded_by`) or `no_longer_applicable` (nothing replaces it)."
        ),
    )
    superseded_by: str | None = Field(
        default=None,
        max_length=_MAX_ID_LENGTH,
        description="The replacing item. Required exactly for superseded_by.",
    )
    retired_by: str | None = Field(
        default=None,
        max_length=_MAX_ACTOR_LENGTH,
        description="Who withdrew the binding.",
    )
    retired_at: str | None = Field(
        default=None,
        description="When it was withdrawn, RFC 3339 UTC to the second.",
    )

    @field_validator("label")
    @classmethod
    def _label_is_an_acceptance_criterion_label(cls, value: str) -> str:
        if not _AC_LABEL_RE.match(value):
            msg = (
                "label must be an acceptance-criterion label (`AC1`, `ac-1`, "
                f"`DoD2`, `AC2b`); rejected: {value!r}"
            )
            raise ValueError(msg)
        return value

    @field_validator("reason")
    @classmethod
    def _reason_is_not_whitespace(cls, value: str) -> str:
        if not value.strip():
            msg = "reason must not be blank"
            raise ValueError(msg)
        return value

    @field_validator("retired_at")
    @classmethod
    def _retired_at_is_a_utc_timestamp(cls, value: str | None) -> str | None:
        if value is not None and not _UTC_TIMESTAMP_RE.match(value):
            msg = (
                "retired_at must be RFC 3339 UTC to the second "
                f"(`2026-10-08T16:20:57Z`); rejected: {value!r}"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _the_typed_reason_is_whole_or_absent(self) -> ModelContractAcBindingRetirement:
        """A typed reason names its replacement; an audit names actor and time."""
        if (
            self.reason_kind is EnumAcBindingRetirementReason.SUPERSEDED_BY
            and not self.superseded_by
        ):
            msg = (
                "reason_kind superseded_by requires `superseded_by`, the replacing item"
            )
            raise ValueError(msg)
        if (
            self.reason_kind is not EnumAcBindingRetirementReason.SUPERSEDED_BY
            and self.superseded_by
        ):
            msg = "`superseded_by` is only valid with reason_kind superseded_by"
            raise ValueError(msg)
        if self.reason_kind is None and (self.retired_by or self.retired_at):
            msg = "retired_by and retired_at are only valid with a typed reason_kind"
            raise ValueError(msg)
        if bool(self.retired_by) != bool(self.retired_at):
            msg = "retired_by and retired_at are recorded together or not at all"
            raise ValueError(msg)
        return self


__all__ = ["ModelContractAcBindingRetirement"]
