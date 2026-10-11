# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregated result of the migration conflict handler."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.migration_conflicts.model_column_violation import (
    ModelColumnViolation,
)
from omnibase_core.models.nodes.migration_conflicts.model_migration_conflict import (
    ModelMigrationConflict,
)

__all__ = ["ModelMigrationConflictReport"]


class ModelMigrationConflictReport(BaseModel):
    """Conflicts per table and, when columns were checked, the column findings.

    columns_checked is False when the request did not ask for the column
    check; column_violations and ambiguous_tables are then empty.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    conflicts: list[ModelMigrationConflict] = Field(default_factory=list)
    columns_checked: bool = False
    column_violations: list[ModelColumnViolation] = Field(default_factory=list)
    ambiguous_tables: list[str] = Field(default_factory=list)
