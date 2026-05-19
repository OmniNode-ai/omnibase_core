# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContractEvidenceProof: artifact-first or behavior-first proof item."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StableProofKind = Literal[
    "model_import",
    "artifact_validation",
    "schema_validation",
    "file_exists",
    "test_passes",
    "receipt_validation",
    "evidence_bundle_validation",
    "runtime_projection_proof",
    "command",
]

_PR_BOUND_PROOF_RE = re.compile(
    r"\bgh\s+pr\s+view\b|github\.com/[^/\s]+/[^/\s]+/pull/\d+\b|/pull/\d+\b|\bpr_number\b",
    re.IGNORECASE,
)


class ModelContractEvidenceProof(BaseModel):
    """Stable proof requirement for a contract.

    A proof item must validate an artifact or behavior. PR-state checks are
    rejected here because PR metadata belongs in ModelEvidenceProvenance.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-id-ok: contract evidence proof IDs are stable human-authored keys, not object UUIDs.
    proof_id: str = Field(..., min_length=1)
    proof_kind: StableProofKind
    description: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    command: str | None = Field(default=None, min_length=1)
    model_path: str | None = Field(default=None, min_length=1)
    artifact_path: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_required_fields(self) -> ModelContractEvidenceProof:
        if self.proof_kind == "model_import" and not self.model_path:
            # error-ok: Pydantic validators must raise ValueError for field validation errors.
            raise ValueError("model_import proof requires model_path")
        if self.proof_kind in {"artifact_validation", "schema_validation"} and (
            not self.model_path or not self.artifact_path
        ):
            # error-ok: Pydantic validators must raise ValueError for field validation errors.
            raise ValueError(
                f"{self.proof_kind} proof requires model_path and artifact_path"
            )
        if self.proof_kind == "file_exists" and not self.artifact_path:
            # error-ok: Pydantic validators must raise ValueError for field validation errors.
            raise ValueError("file_exists proof requires artifact_path")
        if self.proof_kind == "command" and not self.command:
            # error-ok: Pydantic validators must raise ValueError for field validation errors.
            raise ValueError("command proof requires command")
        self._reject_pr_bound_stable_proof()
        return self

    def _reject_pr_bound_stable_proof(self) -> None:
        combined = "\n".join((self.target, self.command or "", self.description))
        if _PR_BOUND_PROOF_RE.search(combined):
            # error-ok: Pydantic validators must raise ValueError for field validation errors.
            raise ValueError(
                "stable proof cannot be PR-number or PR-state bound; "
                "put PR metadata in ModelEvidenceProvenance"
            )


__all__: list[str] = ["ModelContractEvidenceProof", "StableProofKind"]
