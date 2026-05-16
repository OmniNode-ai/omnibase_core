# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from omnibase_core.models.benchmark.model_generation_attempt import (
    ModelGenerationAttempt,
)


class ModelGenerationBenchmark(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID
    track_id: str  # string-id-ok: semantic label ("track_a"/"track_b"), not a UUID
    provider: str
    model_id: str  # string-id-ok: human-readable model label (e.g. "gemini-flash")
    endpoint_class: str
    usage_source: str
    cost_basis: str
    task_description: str
    attempts: list[ModelGenerationAttempt]
    total_latency_e2e_ms: int
    contract_passed: bool
    cost_inference_usd: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_to_contract_pass_usd(self) -> float:
        return self.cost_inference_usd if self.contract_passed else -1.0
