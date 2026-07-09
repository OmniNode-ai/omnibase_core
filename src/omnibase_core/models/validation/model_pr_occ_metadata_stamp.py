# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregate OCC evidence-stamp for a PR (OMN-14187).

Piece 1/5 of the canonical OCC stamp-model (parent epic OMN-14180). This is the
top-level typed vocabulary that both the receipt-gate
(``validator_receipt_gate`` / ``occ-preflight.yml``) and the omnimarket OCC
autobind effect (``adapter_occ_autobind`` / ``adapter_occ_contract``) will
consume, replacing today's independent regex/f-string implementations.

* ``evidence_tickets`` are normalized to the ``OMN-<n>`` shape parsed today by
  ``validator_receipt_gate.EVIDENCE_TICKET_PATTERN`` / ``TICKET_PATTERN``, then
  de-duplicated preserving first-seen order (deliberately NOT sorted, unlike the
  ad-hoc ``_extract_ticket_ids`` helper).
* ``body_sections`` is empty when constructing a fresh stamp to render, and
  populated when a parser decomposes an existing body — the structural
  round-trip surface Piece 2's render()/parse() pair operates over.

Pure Pydantic domain model: zero I/O, zero renderer/parser logic (deferred to
Piece 2 / OMN-14188).
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.validation.model_pr_body_section import ModelPrBodySection
from omnibase_core.models.validation.model_pr_evidence_source import (
    ModelPrEvidenceSource,
)
from omnibase_core.models.validation.model_pr_receipt_gate_skip_token import (
    ModelPrReceiptGateSkipToken,
)

# Case-insensitive by construction: tokens are upper-cased before matching.
# Mirrors the OMN-<n> shape of validator_receipt_gate.TICKET_PATTERN /
# EVIDENCE_TICKET_PATTERN.
_TICKET_RE = re.compile(r"^OMN-\d+$")


class ModelPrOccMetadataStamp(BaseModel):
    """The full typed OCC evidence-stamp decomposed from (or rendered to) a PR."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(default="")
    pr_number: int | None = Field(default=None, ge=1)
    head_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,40}$")
    evidence_source: ModelPrEvidenceSource | None = Field(default=None)
    evidence_tickets: tuple[str, ...] = Field(default_factory=tuple)
    skip_tokens: tuple[ModelPrReceiptGateSkipToken, ...] = Field(default_factory=tuple)
    body_sections: tuple[ModelPrBodySection, ...] = Field(default_factory=tuple)

    @field_validator("evidence_tickets", mode="before")
    @classmethod
    def _normalize_tickets(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str) or not isinstance(value, (list, tuple)):
            raise ValueError(
                "evidence_tickets must be a sequence of OMN-<n> ticket ids, "
                f"got {type(value).__name__}"
            )
        seen: set[str] = set()
        normalized: list[str] = []
        for raw in value:
            if not isinstance(raw, str):
                raise ValueError(
                    f"evidence ticket must be a string, got {type(raw).__name__}"
                )
            token = raw.strip().upper()
            if not _TICKET_RE.fullmatch(token):
                raise ValueError(
                    f"evidence ticket {raw!r} does not match OMN-<n> (e.g. OMN-14187)"
                )
            if token not in seen:
                seen.add(token)
                normalized.append(token)
        return tuple(normalized)

    def as_dict(self) -> dict[str, object]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "evidence_source": (
                self.evidence_source.as_dict()
                if self.evidence_source is not None
                else None
            ),
            # Order-preserving, not sorted — first-seen ticket order is meaningful.
            "evidence_tickets": list(self.evidence_tickets),
            "skip_tokens": [token.as_dict() for token in self.skip_tokens],
            "body_sections": [section.as_dict() for section in self.body_sections],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["ModelPrOccMetadataStamp"]
