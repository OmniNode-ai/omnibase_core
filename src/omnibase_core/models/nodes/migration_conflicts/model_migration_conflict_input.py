# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit snapshot supplied to the pure migration conflict handler."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.migration_conflicts.model_repo_source_file import (
    ModelRepoSourceFile,
)

__all__ = ["ModelMigrationConflictInput"]


class ModelMigrationConflictInput(BaseModel):
    """What the migration conflict handler decides over, without filesystem access.

    sql_files are the migration files in discovery order.
    inventory_boundaries maps a migration file's resolved path to the logical
    database the migration inventory assigns it. python_files are the
    src/ Python sources scanned for column references when
    check_columns is set, in discovery order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sql_files: list[ModelRepoSourceFile] = Field(default_factory=list)
    inventory_boundaries: dict[str, str] = Field(default_factory=dict)
    check_columns: bool = False
    python_files: list[ModelRepoSourceFile] = Field(default_factory=list)
