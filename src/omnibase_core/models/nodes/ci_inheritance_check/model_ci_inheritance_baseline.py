# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shrink-only CI inheritance baseline of one typed repository (OMN-21277)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_ci_repository_type import EnumCiRepositoryType

__all__ = ["ModelCiInheritanceBaseline"]


class ModelCiInheritanceBaseline(BaseModel):
    """The repository-specific inline jobs a typed repository still carries.

    Each entry is ``<workflow file>:jobs.<job id>``. The list only shrinks: the
    ci-repository-jobs handler refuses an inline job it does not list, an
    entry the base baseline did not list, and an entry naming no inline job.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(min_length=1)
    repository_type: EnumCiRepositoryType
    entries: tuple[str, ...] = Field(default=())

    @field_validator("entries")
    @classmethod
    def _unique(cls, entries: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for entry in entries:
            if entry in seen:
                raise ValueError(f"duplicate baseline entry {entry!r}")
            seen.add(entry)
        return entries
