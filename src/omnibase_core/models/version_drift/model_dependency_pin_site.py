# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A handshake pin site of a downstream repository (OMN-21478)."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyPinSite"]


class ModelDependencyPinSite(BaseModel):
    """A file and the regex over the SHA it pins; scripts/pin_bump.py rewrites it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
