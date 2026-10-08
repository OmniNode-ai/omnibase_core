# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One evidence verification check and the observation supporting its outcome."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    computed_field,
    field_validator,
    model_validator,
)

from omnibase_core.enums.enum_evidence_verification_status import (
    EnumEvidenceVerificationStatus,
)


class ModelEvidenceVerifierCheck(BaseModel):
    """Require evidence on passing, failing and indeterminate checks alike.

    ``ok=False`` with ``indeterminate=True`` records an unestablished probe,
    rather than asserting that the evidence proved a failure. An unestablished
    check cannot also pass.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., min_length=1)
    ok: StrictBool
    evidence: str = Field(..., min_length=1)
    indeterminate: StrictBool = False

    @field_validator("name", "evidence")
    @classmethod
    def _require_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("check name and evidence must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def _refuse_passing_indeterminate(self) -> ModelEvidenceVerifierCheck:
        if self.ok and self.indeterminate:
            raise ValueError("a check cannot be both passing and indeterminate")
        return self

    @property
    def outcome(self) -> EnumEvidenceVerificationStatus:
        """Derive the check outcome from its established observations."""
        if self.ok:
            return EnumEvidenceVerificationStatus.PASS
        if self.indeterminate:
            return EnumEvidenceVerificationStatus.INDETERMINATE
        return EnumEvidenceVerificationStatus.FAIL

    outcome = computed_field(outcome)


__all__ = ["ModelEvidenceVerifierCheck"]
