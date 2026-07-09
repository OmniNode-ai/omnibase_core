# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed capture of a PR ``Evidence-Source:`` line (OMN-14187).

Piece 1/5 of the canonical OCC stamp-model (parent epic OMN-14180). This model
is the single typed vocabulary for the two independent regex/f-string
implementations that parse and render evidence sources today:

* ``omnibase_core.validation.validator_receipt_gate`` — ``EVIDENCE_SOURCE_OCC_PR_PATTERN``
  (``^Evidence-Source:\\s+OCC#(\\d+)\\s*$``) and ``EVIDENCE_SOURCE_SHA_PATTERN``
  (``^Evidence-Source:\\s+([0-9a-f]{7,40})\\s*$``).
* ``omnimarket`` ``adapter_occ_autobind._patch_evidence_source`` — the ``OCC#<n>``
  f-string it PATCHes back onto the product PR body.

Pure Pydantic domain model: zero I/O, zero renderer/parser logic. The
deterministic renderer/parser that consumes this vocabulary is deferred to
Piece 2 (OMN-14188).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_pr_evidence_source_kind import EnumPrEvidenceSourceKind


class ModelPrEvidenceSource(BaseModel):
    """A single ``Evidence-Source:`` reference — an OCC PR or a commit SHA.

    Exactly one of ``occ_pr_number`` / ``commit_sha`` is populated, and which
    one is populated must agree with ``kind``. The ``commit_sha`` pattern
    mirrors ``validator_receipt_gate.EVIDENCE_SOURCE_SHA_PATTERN`` (7-40 hex).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumPrEvidenceSourceKind
    occ_pr_number: int | None = Field(default=None, ge=1)
    commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,40}$")
    url: str | None = Field(default=None)

    @model_validator(mode="after")
    def _check_kind_consistency(self) -> ModelPrEvidenceSource:
        if self.kind is EnumPrEvidenceSourceKind.OCC_PR:
            if self.occ_pr_number is None:
                raise ValueError("kind=OCC_PR requires occ_pr_number to be set")
            if self.commit_sha is not None:
                raise ValueError("kind=OCC_PR requires commit_sha to be None")
        else:  # EnumPrEvidenceSourceKind.COMMIT_SHA
            if self.commit_sha is None:
                raise ValueError("kind=COMMIT_SHA requires commit_sha to be set")
            if self.occ_pr_number is not None:
                raise ValueError("kind=COMMIT_SHA requires occ_pr_number to be None")
        return self

    def render_token(self) -> str:
        """Return the source token as it appears after ``Evidence-Source: ``.

        ``OCC#<n>`` for an OCC PR, or the raw commit SHA. Matches the f-string
        emitted by ``adapter_occ_autobind`` today.
        """
        if self.occ_pr_number is not None:
            return f"OCC#{self.occ_pr_number}"
        if self.commit_sha is not None:
            return self.commit_sha
        # Unreachable: the after-validator guarantees exactly one is set.
        # error-ok: defensive invariant guard for an impossible state.
        raise ValueError("evidence source has neither occ_pr_number nor commit_sha")

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "occ_pr_number": self.occ_pr_number,
            "commit_sha": self.commit_sha,
            "url": self.url,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["ModelPrEvidenceSource"]
