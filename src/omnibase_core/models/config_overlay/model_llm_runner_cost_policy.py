# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI runner cost policy for avoidance estimates (OMN-19391).

Ported from infra ``models/pricing/model_runner_cost_policy.py`` (plan C2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLlmRunnerCostPolicy(BaseModel):
    """The hosted-runner baseline price per runner minute."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    github_hosted_per_minute_usd: float = Field(
        ..., ge=0.0, description="Hosted runner cost per runner minute in USD."
    )


__all__ = ["ModelLlmRunnerCostPolicy"]
