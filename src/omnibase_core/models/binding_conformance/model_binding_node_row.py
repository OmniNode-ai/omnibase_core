# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One node's row of the caller's protocol table."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelBindingNodeRow(BaseModel):
    """The protocol codes a node must declare, exactly. An empty row is a pure node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(min_length=1)
    protocols: tuple[str, ...] = ()
