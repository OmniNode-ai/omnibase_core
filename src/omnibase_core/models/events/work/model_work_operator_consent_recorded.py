# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Operator-consent work event (OMN-16177, typed work ledger).

The durable authorization row of rule 18, as a typed event: the operator's
words verbatim, the scope approved and the scope that is not. Both lists are
required and neither may name nothing, because the out-of-scope list is the
half that bounds the grant. A credential rotation also names its approver
(rule 22).

The placeholder and approver sets are copied as data from the rolling ledger's
row grammar (``ledger_grammar.PLACEHOLDER_VALUES`` and the rule 22 approver
set) so the typed and the markdown forms refuse the same rows. Plan task T10
adds the cross-repo equality test.
"""

from __future__ import annotations

from typing import Final, Literal, get_args

from pydantic import Field, field_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import (
    SUMMARY_MAX_LENGTH,
    ModelWorkEventBase,
)

__all__ = [
    "CONSENT_APPROVERS",
    "SCOPE_PLACEHOLDER_VALUES",
    "ConsentApprover",
    "ModelWorkOperatorConsentRecorded",
]

ConsentApprover = Literal["operator", "jake"]
"""Who may approve a credential rotation (rule 22). No agent or lane is one."""

CONSENT_APPROVERS: Final[frozenset[str]] = frozenset(get_args(ConsentApprover))

SCOPE_PLACEHOLDER_VALUES: Final[frozenset[str]] = frozenset(
    {"", "-", "--", ".", "none", "n/a", "na", "nil", "tbd", "nothing", "?"}
)
"""Scope entries that name nothing. Compared after strip, lower-case and one
trailing-dot removal, the same normalisation the ledger grammar applies."""

_SCOPE_ENTRY_MAX_LENGTH = 500


def _names_nothing(entry: str) -> bool:
    return entry.strip().lower().rstrip(".") in SCOPE_PLACEHOLDER_VALUES


class ModelWorkOperatorConsentRecorded(ModelWorkEventBase):
    """Operator consent to a gated action. The durable authorization evidence."""

    kind: Literal[EnumWorkEventKind.CONSENT_RECORDED] = Field(
        default=EnumWorkEventKind.CONSENT_RECORDED, frozen=True
    )
    operator_words: str = Field(
        ...,
        min_length=1,
        max_length=SUMMARY_MAX_LENGTH,
        description="The operator's words, verbatim. Never read by a checker.",
    )
    approved_by: ConsentApprover | None = Field(
        default=None,
        description="The rule 22 approver, required by a credential rotation.",
    )
    approved_scope: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="What the consent approves. At least one entry; no placeholder.",
    )
    out_of_scope: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="What the consent does not approve. At least one entry; no placeholder.",
    )

    @field_validator("operator_words")
    @classmethod
    def _reject_blank_words(cls, raw: str) -> str:
        if not raw.strip():
            raise ValueError("operator_words must not be blank or whitespace-only")
        return raw

    @field_validator("approved_scope", "out_of_scope")
    @classmethod
    def _reject_placeholders(cls, raw: tuple[str, ...]) -> tuple[str, ...]:
        for entry in raw:
            if _names_nothing(entry):
                raise ValueError(
                    f"scope entry {entry!r} names nothing; a scope list that names "
                    "nothing bounds nothing (rule 18)"
                )
            if len(entry) > _SCOPE_ENTRY_MAX_LENGTH:
                raise ValueError(
                    f"scope entry is longer than {_SCOPE_ENTRY_MAX_LENGTH} characters"
                )
        return raw
