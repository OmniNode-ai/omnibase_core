# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Two or more migrations that create one table inside one logical database."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_migration_conflict_type import EnumMigrationConflictType
from omnibase_core.models.nodes.boundary_validation.model_migration_table_definition import (
    ModelMigrationTableDefinition,
)

__all__ = ["ModelMigrationConflict"]


class ModelMigrationConflict(BaseModel):
    """The conflicting definitions of one table, in scan order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    conflict_type: EnumMigrationConflictType
    table_name: str
    definitions: tuple[ModelMigrationTableDefinition, ...]
