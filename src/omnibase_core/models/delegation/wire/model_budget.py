# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Budget limits wire DTO for delegation requests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_budget_action import EnumBudgetAction

__all__: list[str] = ["EnumBudgetAction", "ModelBudgetLimits"]


class ModelBudgetLimits(BaseModel):
    """Declared budget ceilings for a delegated task execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_tokens: int = Field(gt=0)
    max_cost_usd: float = Field(gt=0.0)
    max_time_s: float = Field(gt=0.0)
