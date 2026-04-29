# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire renamed field model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelWireRenamedField(BaseModel):
    """A renamed field tracking an active or retired shim."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    producer_name: str = Field(..., description="Name emitted by the producer")
    canonical_name: str = Field(..., description="Canonical name in the contract")
    shim_status: Literal["active", "retired"] = Field(
        ..., description="Lifecycle state of the rename shim"
    )
    retirement_ticket: str = Field(
        default="", description="Ticket tracking shim retirement"
    )
