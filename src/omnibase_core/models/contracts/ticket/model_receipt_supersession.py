# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelReceiptSupersession — net-new correction record for a DoD receipt.

OMN-13888 scope item 3: supersession / tombstone records let a prior receipt be
re-bound or invalidated WITHOUT editing any merged file. A supersession is a
net-new file appended alongside the base receipt at::

    drift/dod_receipts/<TICKET>/<EVIDENCE_ITEM>/<CHECK_TYPE>.supersede.<NNNN>.yaml

The highest ``NNNN`` in a key's chain is the authoritative record ("latest
non-tombstoned record"). A record with ``tombstone: true`` and no
``replacement`` invalidates the key (the key then has no active receipt). A
record with a ``replacement`` re-binds the key to that receipt — and a later
record can un-tombstone a key by supplying a replacement at a higher ``NNNN``.
The base receipt file is never edited, honoring the append-only rule.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt

_TICKET_ID_RE = re.compile(r"^OMN-\d+$")
# SemVer 2.0.0 — mirrors ``_SEMVER_RE`` in model_dod_receipt.
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class ModelReceiptSupersession(BaseModel):
    """A net-new record that re-binds or tombstones a prior DoD receipt.

    Frozen and ``extra="forbid"``: a supersession is durable evidence, not a
    scratch object. ``replacement`` is required unless ``tombstone`` is set; a
    present replacement must key-match the record (same ticket / evidence item /
    check type) and must carry a per-entry ``contract_entry_sha256`` (new
    scheme) so the correction cannot re-introduce a whole-file binding.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: str = Field(
        ..., description="SemVer 2.0.0 string for the supersession record schema."
    )
    ticket_id: str = Field(
        ..., description="Linear ticket this record corrects (e.g. OMN-13899)."
    )
    # string-id-ok: evidence item IDs are human-readable slugs from the contract.
    evidence_item_id: str = Field(
        ..., min_length=1, description="dod_evidence[].id whose receipt is corrected."
    )
    check_type: str = Field(
        ..., min_length=1, description="check_type of the receipt being corrected."
    )
    supersedes: str = Field(
        ...,
        min_length=1,
        description=(
            "OCC-root-relative path of the receipt or record this one replaces "
            "(e.g. drift/dod_receipts/OMN-13899/dod-x/command.yaml)."
        ),
    )
    reason: str = Field(
        ..., min_length=1, description="Why the prior receipt is superseded."
    )
    superseder: str = Field(
        ...,
        min_length=1,
        description="Identity that authored this correction (agent / login / CI).",
    )
    created_at: datetime = Field(
        ..., description="UTC timestamp when this record was authored (tz-aware)."
    )
    tombstone: bool = Field(
        default=False,
        description=(
            "When true the key is invalidated and has no active receipt unless a "
            "later record supplies a replacement. Requires replacement to be None."
        ),
    )
    replacement: ModelDodReceipt | None = Field(
        default=None,
        description=(
            "The receipt that becomes active for the key. Required unless "
            "tombstone is set. Must key-match this record and carry "
            "contract_entry_sha256."
        ),
    )

    @field_validator("ticket_id")
    @classmethod
    def _validate_ticket_id(cls, v: str) -> str:
        if not _TICKET_ID_RE.match(v):
            raise ValueError(f"ticket_id must match OMN-\\d+, got: {v!r}")
        return v

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(
                f"schema_version must be valid SemVer (e.g. '1.0.0'), got: {v!r}"
            )
        return v

    @field_validator("superseder", "reason")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must contain non-whitespace characters")
        return v

    @field_validator("created_at")
    @classmethod
    def _validate_tz_aware(cls, v: Any) -> datetime:
        if not isinstance(v, datetime):
            raise ValueError(f"created_at must be datetime, got {type(v).__name__}")
        if v.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def _enforce_replacement_invariant(self) -> ModelReceiptSupersession:
        if self.tombstone:
            if self.replacement is not None:
                raise ValueError(
                    "a tombstone record must not carry a replacement receipt; "
                    "set tombstone=false to re-bind the key"
                )
            return self
        if self.replacement is None:
            raise ValueError(
                "a non-tombstone supersession must carry a replacement receipt "
                "(or set tombstone=true to invalidate the key)"
            )
        replacement = self.replacement
        key = (self.ticket_id, self.evidence_item_id, self.check_type)
        replacement_key = (
            replacement.ticket_id,
            replacement.evidence_item_id,
            replacement.check_type,
        )
        if key != replacement_key:
            raise ValueError(
                f"replacement receipt key {replacement_key} does not match the "
                f"supersession record key {key}"
            )
        if replacement.contract_entry_sha256 is None:
            raise ValueError(
                "replacement receipt must carry a per-entry contract_entry_sha256 "
                "(new scheme); whole-file-only bindings are not accepted in a "
                "supersession replacement"
            )
        return self


__all__ = ["ModelReceiptSupersession"]
