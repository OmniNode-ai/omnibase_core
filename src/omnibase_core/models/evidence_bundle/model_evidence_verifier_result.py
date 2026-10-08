# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEvidenceVerifierResult — outcome of an evidence bundle verification run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from omnibase_core.enums.enum_evidence_verification_status import (
    EnumEvidenceVerificationStatus,
)
from omnibase_core.models.evidence_bundle.model_evidence_verifier_check import (
    ModelEvidenceVerifierCheck,
)
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity


class ModelEvidenceVerifierResult(BaseModel):
    """Result produced by a verifier that checked an evidence bundle.

    ``status`` is derived, never an input: PASS iff every check passed. A
    failed check yields FAIL; otherwise an unestablished check yields
    INDETERMINATE. Empty or duplicate check sets are refused.

    ``verifier`` reuses the runtime identity stamp to identify the process
    that ran the checks, including its host, execution locus and code. It is
    structured provenance, not authentication of the verifier or proof that
    the recorded observations actually measured the claimed behavior.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str
    verifier: ModelRuntimeIdentity
    checks: tuple[ModelEvidenceVerifierCheck, ...] = Field(..., min_length=1)

    @field_validator("checks")
    @classmethod
    def _require_distinct_checks(
        cls, checks: tuple[ModelEvidenceVerifierCheck, ...]
    ) -> tuple[ModelEvidenceVerifierCheck, ...]:
        names = [check.name for check in checks]
        if len(set(names)) != len(names):
            raise ValueError("duplicate check names are not allowed")
        return checks

    @property
    def status(self) -> EnumEvidenceVerificationStatus:
        """Derive a verdict without relabeling unknown observations as failures.

        An established failure takes precedence over indeterminate checks;
        those checks retain their individual INDETERMINATE outcomes.
        """
        if any(
            check.outcome is EnumEvidenceVerificationStatus.FAIL
            for check in self.checks
        ):
            return EnumEvidenceVerificationStatus.FAIL
        if any(check.indeterminate for check in self.checks):
            return EnumEvidenceVerificationStatus.INDETERMINATE
        return EnumEvidenceVerificationStatus.PASS

    status = computed_field(status)


__all__ = ["ModelEvidenceVerifierResult"]
