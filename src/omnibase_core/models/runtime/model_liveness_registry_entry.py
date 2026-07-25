# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-surface demand-aware liveness declaration.

OMN-15126 implementation of the OMN-14845 design (design §4).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.runtime.model_demand_source_ref import ModelDemandSourceRef
from omnibase_core.models.runtime.model_liveness_artifact_ref import ModelArtifactRef
from omnibase_core.models.runtime.model_output_join_spec import ModelOutputJoinSpec
from omnibase_core.models.runtime.model_sampling_policy import ModelSamplingPolicy

__all__ = ["ModelLivenessRegistryEntry"]


class ModelLivenessRegistryEntry(BaseModel):
    """Per-surface liveness declaration (design §4).

    Placement of registry entry *instances* (centralized catalog vs.
    per-node ``contract.yaml`` extension) is OPEN-3 in the design and is not
    resolved by this schema — this model is the shape a resolved instance
    must have, independent of where instances are stored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    surface_id: str = Field(
        ...,
        min_length=1,
        description="Stable slug, e.g. 'omnimarket.node_occ_attestation_observe'.",
    )
    owner: str = Field(..., min_length=1, description="Team/person handle.")
    lane: str = Field(
        ..., min_length=1, description="dev | stability-test | prod | correction-lab."
    )
    demand_source: ModelDemandSourceRef
    expected_output_join: ModelOutputJoinSpec
    artifact_ref: ModelArtifactRef
    freshness_slo_seconds: int = Field(..., ge=1)
    error_budget_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="None == 0.0 (zero-tolerance default; design §3.2 step 3).",
    )
    sampling_policy: ModelSamplingPolicy | None = Field(default=None)
    allowed_synthetic_predicates: tuple[str, ...] = Field(default_factory=tuple)
    mandatory_for_transitions: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def effective_error_budget_ratio(self) -> float:
        """``error_budget_ratio`` with the None==0.0 default applied (design §3.2 step 3)."""
        return self.error_budget_ratio if self.error_budget_ratio is not None else 0.0
