# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The committed omnimarket validator inventory document (OMN-21503)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_omnimarket_validator_inventory_entry import (
    ModelOmnimarketValidatorInventoryEntry,
)

__all__ = ["ModelOmnimarketValidatorInventory"]


class ModelOmnimarketValidatorInventory(BaseModel):
    """Every validator-shaped script and node resident in omnimarket."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Inventory schema version")
    entries: tuple[ModelOmnimarketValidatorInventoryEntry, ...] = Field(
        description="One entry per resident script or node"
    )
