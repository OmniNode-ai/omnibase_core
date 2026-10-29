# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed input for the receipt re-probe COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelReceiptReprobeCheckInput(BaseModel):
    """Receipt tree whose recorded probes are re-executed."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipts_dir: str = Field(
        default="drift/dod_receipts",
        min_length=1,
        description="Directory tree containing ModelDodReceipt YAML files.",
    )
