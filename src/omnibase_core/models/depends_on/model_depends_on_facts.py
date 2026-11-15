# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What exists in the world, by kind, read as data (OMN-24537)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDependsOnFacts(BaseModel):
    """For each kind, every token that exists; a kind the facts do not speak of holds nothing."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    present: dict[str, tuple[str, ...]] = Field(
        default_factory=dict,
        description="Existing tokens by kind",
    )

    def has_kind(self, kind: str) -> bool:
        """Whether the facts speak about the kind at all."""
        return kind in self.present

    def holds(self, kind: str, token: str) -> bool:
        """Whether a token of a kind exists in the world."""
        return token in self.present.get(kind, ())
