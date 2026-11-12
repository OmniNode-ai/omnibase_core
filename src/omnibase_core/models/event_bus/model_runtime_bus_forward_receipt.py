# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The receipt a forwarder answers after carrying recorded events to the hosted bus."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRuntimeBusForwardReceipt(BaseModel):
    """What the forwarder says about the events it carried."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    forwarded: int = Field(ge=0)
    failed: int = Field(ge=0)
    detail: str | None = Field(
        default=None, description="what the forwarder says when failed > 0"
    )


__all__: list[str] = ["ModelRuntimeBusForwardReceipt"]
