# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One table defined more than once inside a logical database boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_migration_conflict_type import (
    EnumMigrationConflictType,
)
from omnibase_core.models.nodes.migration_conflicts.model_migration_table_definition import (
    ModelMigrationTableDefinition,
)

__all__ = ["ModelMigrationConflict"]


class ModelMigrationConflict(BaseModel):
    """A NAME_CONFLICT (columns differ) or EXACT_DUPLICATE (columns equal)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    conflict_type: EnumMigrationConflictType
    table_name: str
    definitions: list[ModelMigrationTableDefinition] = Field(default_factory=list)
