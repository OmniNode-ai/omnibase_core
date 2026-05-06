# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRepoFilter — scope predicate filter targeting repository kind."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRepoFilter(BaseModel):
    """Predicate filter targeting repository kind."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(
        description=(
            "Repository kind identifier. Common values: 'omninode', 'external'. "
            "Matched against the resolved EnumScopeToken for the current cwd."
        )
    )


__all__ = ["ModelRepoFilter"]
