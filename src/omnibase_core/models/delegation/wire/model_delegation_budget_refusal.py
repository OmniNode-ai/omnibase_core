# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed refusal recorded when dispatch cannot honour a requested timeout."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_delegation_budget_refusal_reason import (
    EnumDelegationBudgetRefusalReason,
)


class ModelDelegationBudgetRefusal(BaseModel):
    """A requested timeout exceeds its task-class ceiling before dispatch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: EnumDelegationBudgetRefusalReason
    task_type: str = Field(min_length=1)
    requested_timeout_seconds: int = Field(ge=1)
    task_class_timeout_ceiling_seconds: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_refusal_truth(self) -> ModelDelegationBudgetRefusal:
        if (
            self.reason
            is EnumDelegationBudgetRefusalReason.TIMEOUT_EXCEEDS_TASK_CLASS_CEILING
        ):
            if (
                self.requested_timeout_seconds
                <= self.task_class_timeout_ceiling_seconds
            ):
                raise ValueError(
                    "timeout ceiling refusal requires requested timeout above ceiling"
                )
        return self


__all__ = ["ModelDelegationBudgetRefusal"]
