# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEvidenceProvenance: transient review/source metadata for evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelEvidenceProvenance(BaseModel):
    """Review and source metadata supporting a stable evidence proof.

    PR metadata belongs here, not in the stable contract proof identity. This
    preserves useful review traceability without making PR numbers the durable
    truth that contracts validate.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., min_length=1)
    commit_sha: str | None = Field(default=None, min_length=7)
    branch: str | None = Field(default=None, min_length=1)
    pr_number: int | None = Field(default=None, ge=1)
    pr_url: str | None = Field(default=None, min_length=1)
    ci_run_url: str | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _require_some_trace(self) -> ModelEvidenceProvenance:
        if not any(
            (
                self.commit_sha,
                self.branch,
                self.pr_number is not None,
                self.pr_url,
                self.ci_run_url,
                self.notes,
            )
        ):
            # error-ok: Pydantic validators must raise ValueError for field validation errors.
            raise ValueError("provenance must include at least one trace field")
        return self


__all__: list[str] = ["ModelEvidenceProvenance"]
