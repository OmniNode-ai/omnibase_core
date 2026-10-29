# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One row of the omnimarket validator inventory (OMN-21503)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validator_inventory_class import (
    EnumValidatorInventoryClass,
)
from omnibase_core.enums.enum_validator_inventory_kind import (
    EnumValidatorInventoryKind,
)

__all__ = ["ModelOmnimarketValidatorInventoryEntry"]


class ModelOmnimarketValidatorInventoryEntry(BaseModel):
    """A script or node resident in omnimarket, its class and its replacement."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(
        description="Repository-relative path of the script or node directory"
    )
    kind: EnumValidatorInventoryKind = Field(description="Script or node")
    validator_class: EnumValidatorInventoryClass = Field(
        description="validator, decision or other"
    )
    replacing_core_validator: str | None = Field(
        default=None,
        description=(
            "Existing omnibase_core validator id that covers a validator entry, "
            "or the checker id that will replace it"
        ),
    )
    replacement_exists: bool = Field(
        default=False,
        description="True when replacing_core_validator already exists in core",
    )
    child_ticket: str | None = Field(
        default=None,
        pattern=r"^OMN-\d+$",
        description="Child ticket of OMN-21503 that migrates this validator",
    )
