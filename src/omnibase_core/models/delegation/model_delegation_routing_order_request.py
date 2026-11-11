# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request sent to the routing order node for a delegated task class."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDelegationRoutingOrderRequest(BaseModel):
    """Asks the routing order node how to serve a task class today."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_class: str = Field(min_length=1)
    tenant_slug: str | None
    surface: str = Field(min_length=1)
    pin_lifted: bool


__all__ = ["ModelDelegationRoutingOrderRequest"]
