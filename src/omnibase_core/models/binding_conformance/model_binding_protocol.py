# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One protocol of the caller's table."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelBindingProtocol(BaseModel):
    """A short code and the import path of the protocol it stands for."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    code: str = Field(min_length=1)
    protocol: str = Field(
        min_length=3, description="Import path in module.path:ClassName form."
    )
