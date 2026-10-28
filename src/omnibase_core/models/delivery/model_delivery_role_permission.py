# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery role permission facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from omnibase_core.enums.enum_delivery_path_role import EnumDeliveryPathRole
from omnibase_core.enums.enum_delivery_reference_kind import EnumDeliveryReferenceKind

__all__ = ["ModelDeliveryRolePermission"]


class ModelDeliveryRolePermission(BaseModel):
    """Immutable delivery role permission data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    role: EnumDeliveryPathRole
    kinds: tuple[EnumDeliveryReferenceKind, ...]

    @field_validator("kinds")
    @classmethod
    def _reject_unknown(
        cls, value: tuple[EnumDeliveryReferenceKind, ...]
    ) -> tuple[EnumDeliveryReferenceKind, ...]:
        if EnumDeliveryReferenceKind.UNKNOWN in value:
            raise ValueError("unknown references cannot be permitted")
        return value
