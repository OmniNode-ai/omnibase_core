# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""All honesty violations found for one receipt file."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_violation import (
    ModelReceiptHonestyViolation,
)


class ModelReceiptHonestyFinding(BaseModel):
    """Honesty violations for one receipt file on disk."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipt_path: str
    violations: list[ModelReceiptHonestyViolation]
