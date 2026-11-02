# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Named source text consumed by the pure FSM checker."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelFsmSourceText(BaseModel):
    """An immutable source label and its contents."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(min_length=1)
    text: str
