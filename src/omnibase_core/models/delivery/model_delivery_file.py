# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery file facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDeliveryFile"]


class ModelDeliveryFile(BaseModel):
    """Immutable delivery file data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    location: str
    text: str
