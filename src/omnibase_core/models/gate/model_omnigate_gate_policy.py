# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate gate policy model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_omnigate import EnumGateResponse


class ModelOmniGateGatePolicy(BaseModel):
    """Policy for handling failed or missing OmniGate receipts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scope: str = Field(default="forks-only")
    on_missing_receipt: EnumGateResponse = Field(default=EnumGateResponse.AUTO_CLOSE)
    close_message: str | None = None
    grace_period_minutes: int = Field(default=10, ge=0)
    exempt_users: tuple[str, ...] = Field(default=())


__all__ = ["ModelOmniGateGatePolicy"]
