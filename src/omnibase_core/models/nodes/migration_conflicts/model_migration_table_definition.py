# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A table definition extracted from one migration file."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelMigrationTableDefinition"]


class ModelMigrationTableDefinition(BaseModel):
    """The lower-cased table name and column names one CREATE TABLE declares."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    table_name: str
    columns: frozenset[str]
    file_path: str
    repo_name: str
