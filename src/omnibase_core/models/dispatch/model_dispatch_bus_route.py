# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pattern B broker route metadata loaded from contract YAML."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelDispatchBusRoute(BaseModel):
    """Resolved broker route for the Pattern B dispatch bus client."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_path: Path = Field(
        ...,
        description="Contract file used to resolve the broker route.",
    )
    command_topic: str = Field(
        ...,
        min_length=1,
        description="Broker command topic to publish the request to.",
    )
    terminal_topic: str = Field(
        ...,
        min_length=1,
        description="Broker terminal topic to wait on for the correlated result.",
    )


__all__ = ["ModelDispatchBusRoute"]
