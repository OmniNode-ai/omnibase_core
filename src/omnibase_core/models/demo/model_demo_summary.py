"""Model for demo validation summary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.enums.enum_demo_recommendation import EnumDemoRecommendation
from omnibase_core.enums.enum_demo_verdict import EnumDemoVerdict
from omnibase_core.models.demo.model_demo_invariant_result import ModelInvariantResult
from omnibase_core.models.demo.model_failure_detail import ModelFailureDetail


class ModelDemoSummary(BaseModel):
    """Summary of demo validation run.

    Aggregates results across all samples and invariants with computed
    recommendation based on pass rate thresholds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total: int = Field(..., ge=0, description="Total number of samples evaluated")
    passed: int = Field(..., ge=0, description="Number of samples that passed")
    failed: int = Field(..., ge=0, description="Number of samples that failed")
    pass_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Pass rate from 0.0 to 1.0"
    )
    verdict: EnumDemoVerdict = Field(..., description="Overall evaluation verdict")
    invariant_results: dict[str, ModelInvariantResult] = Field(
        ..., description="Per-invariant breakdown of results"
    )
    failures: list[ModelFailureDetail] = Field(
        default_factory=list, description="Detailed list of failures"
    )

    # NOTE(OMN-1206): Pydantic @computed_field requires @property below it.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def recommendation(self) -> EnumDemoRecommendation:
        """Compute promotion recommendation based on pass rate.

        - pass_rate == 1.0: promote (perfect score)
        - pass_rate >= 0.9: promote_with_review (minor issues)
        - pass_rate < 0.9: reject (significant issues)
        """
        if self.pass_rate == 1.0:
            return EnumDemoRecommendation.PROMOTE
        if self.pass_rate >= 0.9:
            return EnumDemoRecommendation.PROMOTE_WITH_REVIEW
        return EnumDemoRecommendation.REJECT


__all__ = ["ModelDemoSummary"]
