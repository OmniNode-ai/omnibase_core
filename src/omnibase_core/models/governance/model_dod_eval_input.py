# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, durable facts consumed by the definition-of-done reducer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dod_eval_verification_status import (
    EnumDodEvalVerificationStatus,
)


class ModelDodEvalInput(BaseModel):
    """The complete, clock-free input contract for one DoD evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: EnumDodEvalVerificationStatus = Field(
        ..., description="Normalized verification status."
    )
    failed_count: int = Field(..., description="Number of failed evidence checks.")
    total_checks: int = Field(..., description="Number of verdict-bearing checks.")
    behavior_proving_count: int = Field(
        ..., description="Number of checks proving claimed behavior."
    )


__all__ = ["ModelDodEvalInput"]
