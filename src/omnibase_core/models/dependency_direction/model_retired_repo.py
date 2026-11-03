# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A repository the organisation has retired, and the names it was referenced by (OMN-22385)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelRetiredRepo"]


class ModelRetiredRepo(BaseModel):
    """A retired repository: no layer, and no repository may reference it.

    Attributes:
        repo: The GitHub repository name (``omnibase_compat``).
        retired_by: The ruling or ticket that retired it, cited in every finding.
        python_modules: Top-level import names its distribution provided.
        distributions: Distribution names it published.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    retired_by: str = Field(min_length=1)
    python_modules: tuple[str, ...] = Field(default=())
    distributions: tuple[str, ...] = Field(default=())
