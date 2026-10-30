# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One honesty rule violation found in a receipt."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelReceiptHonestyViolation(BaseModel):
    """One violated honesty rule with its explanation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rule: str  # EnumHonestyRule value; the enum lives in validation (layering)
    detail: str
