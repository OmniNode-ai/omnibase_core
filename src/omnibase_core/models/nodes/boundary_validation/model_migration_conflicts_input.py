# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit snapshot supplied to the pure migration conflict check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

__all__ = ["ModelMigrationConflictsInput"]


class ModelMigrationConflictsInput(BaseModel):
    """What the migration conflict check decides over, without filesystem access.

    Every path is ``<repo>/<repo-relative path>`` in POSIX form. ``migration_files``
    holds the SQL migration files in scan order. ``python_files`` holds the
    ``<repo>/src/**/*.py`` sources scanned when ``check_columns`` is set.
    ``inventory_yaml`` maps migration files to logical databases; ``None`` means
    no inventory, so every table shares one conflict boundary.
    ``suppressed_tables`` are lowercased table names reported as suppressed
    rather than as conflicts. ``warn_columns`` reports column-reference
    violations as warnings instead of failures.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    migration_files: list[ModelSourceFile] = Field(default_factory=list)
    python_files: list[ModelSourceFile] = Field(default_factory=list)
    inventory_yaml: str | None = None
    suppressed_tables: list[str] = Field(default_factory=list)
    check_columns: bool = False
    warn_columns: bool = False
