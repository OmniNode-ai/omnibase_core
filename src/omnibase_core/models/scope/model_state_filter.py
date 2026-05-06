# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelStateFilter — scope predicate filter targeting required runtime state markers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelStateFilter(BaseModel):
    """Predicate filter targeting required runtime state markers."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    requires: list[str] = Field(
        default_factory=list,
        description=(
            "List of required state markers: env var names or directory paths. "
            "All must be present for the predicate to match."
        ),
    )


__all__ = ["ModelStateFilter"]
