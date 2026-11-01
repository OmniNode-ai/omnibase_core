# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validated registry and scope queries (OMN-21565)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .model_invariant_entry import ModelInvariantEntry

__all__ = ["ModelInvariantRegistry"]


class ModelInvariantRegistry(BaseModel):
    """Validated registry and scope queries."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    scopes: tuple[str, ...] = Field(description="Known scope tags")
    invariants: tuple[ModelInvariantEntry, ...] = Field(description="Validated entries")
    active_status: str = Field(description="Contract-defined active lifecycle status")

    def by_id(self) -> dict[str, ModelInvariantEntry]:
        """Index entries by identifier."""
        return {entry.id: entry for entry in self.invariants}

    def active_for_scopes(
        self, scopes: frozenset[str]
    ) -> tuple[ModelInvariantEntry, ...]:
        """Select active entries intersecting the supplied scope tags."""
        return tuple(
            entry
            for entry in self.invariants
            if entry.status == self.active_status and scopes.intersection(entry.scope)
        )
