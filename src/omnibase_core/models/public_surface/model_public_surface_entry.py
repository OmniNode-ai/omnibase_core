# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One public surface item and where it is declared."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_public_surface_kind import EnumPublicSurfaceKind


class ModelPublicSurfaceEntry(BaseModel):
    """A single public-surface entry: repo, kind, identity, declaration site."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    kind: EnumPublicSurfaceKind
    identity: str = Field(min_length=1)
    path: str = Field(min_length=1)
    line: int = Field(ge=1)
    references: tuple[str, ...] = ()
    renamed_to: str | None = None

    @property
    def key(self) -> str:
        """Stable key used to index consumers: repo:kind:identity."""
        return f"{self.repo}:{self.kind.value}:{self.identity}"
