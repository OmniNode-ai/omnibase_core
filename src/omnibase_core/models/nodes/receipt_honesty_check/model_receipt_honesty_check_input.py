# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed input for the receipt honesty COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelReceiptHonestyCheckInput(BaseModel):
    """Receipt tree, or explicit receipt files, to scan for honesty violations."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipts_dir: str = Field(
        default="drift/dod_receipts",
        min_length=1,
        description="Root of the dod_receipts/ tree to scan.",
    )
    receipt_paths: list[str] = Field(
        default_factory=list,
        description=(
            "Explicit receipt YAML files to scan; when non-empty, receipts_dir is "
            "not walked."
        ),
    )
