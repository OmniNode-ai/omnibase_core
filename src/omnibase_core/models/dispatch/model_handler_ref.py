# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler class reference model for contract handler_routing (OMN-7654)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelHandlerRef(BaseModel):
    """Reference to a handler class in a contract's handler_routing section."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., description="Handler class name")
    module: str = Field(..., description="Fully qualified module path")


__all__ = ["ModelHandlerRef"]
