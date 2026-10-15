# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One `uses:` reference to a repository of the organization (OMN-17427)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCiOrgReference"]


class ModelCiOrgReference(BaseModel):
    """A reusable workflow or action reference read from a workflow file."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    line: int = Field(ge=1)
    repository: str = Field(min_length=1)
    target: str = Field(
        min_length=1, description="<org>/<repo>[/<path>] without the @ref"
    )
