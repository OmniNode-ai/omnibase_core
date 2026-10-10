# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A table created by one SQL migration file."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelMigrationTableDefinition"]


class ModelMigrationTableDefinition(BaseModel):
    """The lowercased table name and column names of one CREATE TABLE statement.

    ``path`` is the migration file as ``<repo>/<repo-relative path>`` and
    ``repo_name`` its first segment.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    table_name: str
    columns: frozenset[str]
    path: str
    repo_name: str
