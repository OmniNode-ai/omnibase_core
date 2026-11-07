# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence for a case evaluated in both presentation orders."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_model_swap_judge_verdict import EnumModelSwapJudgeVerdict


class ModelModelSwapValidationCase(BaseModel):
    """A case identifier, both ordered verdicts and the reported score."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, allow_inf_nan=False
    )

    case_id: str = Field(min_length=1)
    verdict_reference_first: EnumModelSwapJudgeVerdict
    verdict_candidate_first: EnumModelSwapJudgeVerdict
    score: float = Field(ge=0, le=1)


__all__ = ["ModelModelSwapValidationCase"]
