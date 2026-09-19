# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared and resolved execution budget evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDelegationBudgetEvidence(BaseModel):
    """Budget truth for an execution attempt; omission is recorded explicitly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    requested_timeout_seconds: int | None = Field(
        description="CLI-requested timeout; null records an omitted CLI argument."
    )
    task_class_timeout_ceiling_seconds: int = Field(ge=1)
    execution_timeout_seconds: int = Field(
        ge=1,
        description="Numeric timeout resolved before dispatch.",
    )
    terminal_delivery_margin_seconds: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_resolved_timeout(self) -> ModelDelegationBudgetEvidence:
        if self.requested_timeout_seconds is not None:
            if self.requested_timeout_seconds < 1:
                raise ValueError(
                    "requested_timeout_seconds must be positive when present"
                )
            if self.requested_timeout_seconds > self.task_class_timeout_ceiling_seconds:
                raise ValueError(
                    "requested_timeout_seconds cannot exceed task class timeout ceiling"
                )
        if self.execution_timeout_seconds > self.task_class_timeout_ceiling_seconds:
            raise ValueError(
                "execution_timeout_seconds cannot exceed task class timeout ceiling"
            )
        return self


__all__ = ["ModelDelegationBudgetEvidence"]
