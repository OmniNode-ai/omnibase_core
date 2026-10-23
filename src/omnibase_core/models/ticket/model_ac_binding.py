# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18236 — one acceptance-criterion binding, pinned and (maybe) accepted.

``binds_ac`` says which criteria an evidence item CLAIMS. It says nothing about
who agreed, or about which revision of the criterion was agreed to. Both
absences are load-bearing:

* **Nobody agreed.** The plan's first rule is that no name-based inference is
  authoritative — a check whose name resembles a criterion binds nothing. A
  mapping is data a reviewer or the evidence author accepted, never a string
  match a machine performed. Without a place to record that acceptance, a
  proposal and a reviewed binding are indistinguishable, which is why autobind
  may not propose at all today (OMN-18238).
* **Nothing said which revision.** A criterion can be rewritten under a check
  that is still passing, and the binding goes on reading as proof of a sentence
  that no longer exists.

A binding therefore carries the criterion's hash always, and an acceptance
record when it has one. A binding with no ``accepted_by`` is a DRAFT: a
proposal, not proof. A binding whose ``criterion_hash`` no longer matches the
ticket is STALE and reverts to unproven until somebody re-accepts it.

OMN-17427. Carried over from onex_change_control unchanged (fields, types,
validators, ``extra="forbid"``) so a product-repo contract that records its
bindings parses here. Until now only OCC declared ``ac_bindings``, and with OCC
retired a product repository validates its contracts against
``ModelTicketContract``, which refused every such entry as an extra input while
the DoD verifier (``node_dod_verify``) reads it.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: A canonical acceptance-criterion label. The same closed shape the
#: ``binds_ac`` validator enforces, so a label cannot be legal in one field and
#: illegal in the other.
#:
#: OMN-18356: the optional single-letter SUFFIX group matches the producer's
#: grammar (``omniclaude`` ``_CRITERION_LABEL``) exactly -- a round split into
#: ``AC2b``/``AC2c``/... sits a letter directly after the ordinal digits, with
#: no boundary between them (both are word characters), so a bare ``(\d+)$``
#: never matched it. The suffix is stored AS WRITTEN (this validator does not
#: canonicalise, same as it never has for a bare ``ac1``): ``AC2b`` and
#: ``AC2B`` are different labels, not the same criterion written twice.
_AC_LABEL_RE = re.compile(r"^(AC|DOD)[-_ .]?(\d+)([a-zA-Z]?)$", re.IGNORECASE)
#: sha256, lowercase hex. Not a prefix and not a truncation: a short hash is a
#: hash that collides sooner and reads as if it did not.
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
#: RFC 3339 UTC, seconds precision, `Z` suffix. One spelling so two records are
#: comparable without a parser.
_UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_MAX_ACTOR_LENGTH = 200


class ModelAcBinding(BaseModel):
    """One criterion, the revision it was pinned to, and who accepted it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    label: str = Field(
        ...,
        description=(
            "The acceptance-criterion label this binding covers (`AC1`, "
            "`DoD2`). Must also appear in the item's `binds_ac`, so the "
            "existing consumers keep reading one list and this record never "
            "becomes a second, disagreeing declaration."
        ),
        max_length=50,
    )
    criterion_hash: str = Field(
        ...,
        description=(
            "sha256 of the criterion's normalised text at the moment this "
            "binding was derived or accepted. When the criterion's text "
            "changes its hash changes, this binding is STALE, and the closer "
            "treats it as absent until it is re-accepted."
        ),
    )
    accepted_by: str = Field(
        default="",
        description=(
            "The reviewer or evidence author who accepted this binding. EMPTY "
            "means this is a DRAFT proposal, which is not evidence and does "
            "not satisfy the closer."
        ),
        max_length=_MAX_ACTOR_LENGTH,
    )
    accepted_at: str = Field(
        default="",
        description=(
            "When it was accepted, RFC 3339 UTC to the second. Empty exactly "
            "when `accepted_by` is empty."
        ),
    )
    proposed_by: str = Field(
        default="",
        description=(
            "What produced this binding when it was not hand-written — the "
            "autobinder's own identifier. Recorded so a reviewer can see they "
            "are accepting a machine's proposal rather than their own reading."
        ),
        max_length=_MAX_ACTOR_LENGTH,
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

    @field_validator("criterion_hash")
    @classmethod
    def _hash_is_a_full_sha256(cls, value: str) -> str:
        if not _SHA256_HEX_RE.match(value):
            msg = (
                "criterion_hash must be a full lowercase sha256 hex digest (64 "
                f"characters); rejected: {value!r}"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _acceptance_is_recorded_whole_or_not_at_all(self) -> ModelAcBinding:
        """An acceptance names both an actor and a time, or it is a draft.

        A record with an actor and no time cannot be audited, and one with a
        time and no actor asserts that something was accepted by nobody. Both
        read as acceptance to a consumer checking only one field, so neither is
        allowed to exist.
        """
        if bool(self.accepted_by) != bool(self.accepted_at):
            msg = (
                "an accepted binding declares BOTH `accepted_by` and "
                "`accepted_at`; a draft declares neither. Got accepted_by="
                f"{self.accepted_by!r}, accepted_at={self.accepted_at!r}"
            )
            raise ValueError(msg)
        if self.accepted_at and not _UTC_TIMESTAMP_RE.match(self.accepted_at):
            msg = (
                "accepted_at must be RFC 3339 UTC to the second "
                f"(`2026-09-12T18:04:20Z`); rejected: {self.accepted_at!r}"
            )
            raise ValueError(msg)
        return self

    @property
    def is_accepted(self) -> bool:
        """True only for a binding a person accepted. A draft is not evidence."""
        return bool(self.accepted_by)


__all__ = ["ModelAcBinding"]
