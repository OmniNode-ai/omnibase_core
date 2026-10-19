# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One internal sibling of the internal sibling pin check (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelInternalSibling"]


class ModelInternalSibling(BaseModel):
    """A repository whose dev merges are tagged, and the distribution it ships.

    Attributes:
        repo: The GitHub repository name under the contract's organisation.
        distribution: The distribution name a consumer declares.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    distribution: str = Field(min_length=1)
