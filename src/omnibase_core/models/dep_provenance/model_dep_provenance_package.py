# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One governed package: its own repository and the source shapes admitted for it."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_dep_provenance_shape import EnumDepProvenanceShape

__all__ = ["ModelDepProvenancePackage"]


class ModelDepProvenancePackage(BaseModel):
    """A row of the contract's package table, parsed."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    name: str
    repository: str
    shapes: tuple[EnumDepProvenanceShape, ...]
