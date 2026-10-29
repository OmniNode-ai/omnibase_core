# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Roots and product-graph cap consumed by the contract walker."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelContractWalkerCheckInput(BaseModel):
    """Directories (or contract.yaml files) to walk and the per-workflow state cap (None keeps the walker default)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    roots: tuple[Path, ...]
    max_product_states: int | None = None
