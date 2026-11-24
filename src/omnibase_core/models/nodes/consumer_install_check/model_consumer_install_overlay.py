# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The overlay that declares consumers, candidates and bounds (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.consumer_install_check.model_candidate_spec import (
    ModelCandidateSpec,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_spec import (
    ModelConsumerSpec,
)


class ModelConsumerInstallOverlay(BaseModel):
    """Consumers, candidates and every bound of the check; nothing else is configured."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int
    python_version: str = Field(min_length=1)
    step_timeout_seconds: float = Field(gt=0)
    total_budget_seconds: float = Field(
        gt=0, description="Bound on one run (OMN-26670 AC4: five minutes)"
    )
    max_parallel: int = Field(ge=1)
    fail_on_unattributed: bool = Field(
        description="When false a failure that does not touch the candidate is reported, not failed"
    )
    consumers: tuple[ModelConsumerSpec, ...] = Field(min_length=1)
    candidates: tuple[ModelCandidateSpec, ...] = Field(min_length=1)
