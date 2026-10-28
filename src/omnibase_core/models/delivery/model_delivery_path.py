# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery path facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_delivery_path_role import EnumDeliveryPathRole

__all__ = ["ModelDeliveryPath"]


class ModelDeliveryPath(BaseModel):
    """Immutable delivery path data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path_name: str = Field(min_length=1)
    producing_repository: str
    consumer_kind: str
    location: str
    role: EnumDeliveryPathRole
    bootstrap_pin: str | None = None
