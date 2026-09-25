# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelUnresolvedField(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    field_name: str = Field(
        ...,
        description="Identity field that could not be resolved",
        min_length=1,
    )
    reason: str = Field(
        ...,
        description="Reason the field could not be resolved",
        min_length=1,
    )


__all__ = ["ModelUnresolvedField"]
