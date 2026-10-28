# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery issue facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_delivery_reference_kind import EnumDeliveryReferenceKind
from omnibase_core.enums.enum_delivery_status import EnumDeliveryStatus

__all__ = ["ModelDeliveryIssue"]


class ModelDeliveryIssue(BaseModel):
    """Immutable delivery issue data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path_name: str | None
    location: str
    consumer_kind: str
    kind: EnumDeliveryReferenceKind
    status: EnumDeliveryStatus
    reference_allowed: bool
    reason: str
    message: str
