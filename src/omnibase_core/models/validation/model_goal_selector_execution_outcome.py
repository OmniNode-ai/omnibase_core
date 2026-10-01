# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, contract-owned pins for cross-repository goal evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelGoalSelectorExecutionOutcome(BaseModel):
    """Observed result for one exact protected verifier test selector."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    selector: str = Field(..., min_length=1, max_length=512)
    outcome: Literal["passed", "failed", "not_run"]

    @field_validator("selector")
    @classmethod
    def _selector_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("test selector must not be blank")
        return value
