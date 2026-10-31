# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic verdict of one experiment, with its reason codes (OMN-21627)."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.enums.enum_retrospective_reason_code import (
    EnumRetrospectiveReasonCode,
)
from omnibase_core.enums.enum_retrospective_verdict import EnumRetrospectiveVerdict
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExperimentVerdict(BaseModel):
    """PASS, FAIL or INSUFFICIENT_EVIDENCE for one experiment, never a narrative.

    A PASS carries no reason code; a FAIL or an INSUFFICIENT_EVIDENCE carries at
    least one, so a result is always explained.

    Attributes:
        experiment_id: The experiment.
        slot: Origin slot.
        verdict: The result.
        reason_codes: Why the result is not a PASS.
        contract_version: Success contract version evaluated.
        evaluator_version: Evaluator version that computed it.
        input_hash: Hash of the evidence snapshot it was computed from.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: UUID
    slot: EnumExperimentSlot
    verdict: EnumRetrospectiveVerdict
    reason_codes: tuple[EnumRetrospectiveReasonCode, ...] = ()
    contract_version: ModelSemVer
    evaluator_version: ModelSemVer
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _reason_codes_explain_the_verdict(self) -> Self:
        passed = self.verdict is EnumRetrospectiveVerdict.PASS
        if passed and self.reason_codes:
            raise ValueError("a PASS verdict carries no reason code")
        if not passed and not self.reason_codes:
            raise ValueError(f"a {self.verdict.value} verdict needs a reason code")
        return self
