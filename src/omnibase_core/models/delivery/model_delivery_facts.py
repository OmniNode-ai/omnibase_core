# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery facts facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.delivery.model_delivery_overlay import ModelDeliveryOverlay
from omnibase_core.models.delivery.model_delivery_path import ModelDeliveryPath
from omnibase_core.models.delivery.model_delivery_ref import ModelDeliveryRef

__all__ = ["ModelDeliveryFacts"]


class ModelDeliveryFacts(BaseModel):
    """Immutable delivery facts data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay: ModelDeliveryOverlay
    paths: tuple[ModelDeliveryPath, ...]
    refs: tuple[ModelDeliveryRef, ...] = ()
    discovered: tuple[ModelDeliveryRef, ...] = ()
    unreadable_locations: tuple[str, ...] = ()
