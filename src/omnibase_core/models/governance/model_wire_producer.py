# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire producer declaration model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWireProducer(BaseModel):
    """Producer declaration in a wire schema contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., description="Repository containing the producer")
    file: str = Field(..., description="Path to producer code")
    function: str = Field(default="", description="Emitting function name")
