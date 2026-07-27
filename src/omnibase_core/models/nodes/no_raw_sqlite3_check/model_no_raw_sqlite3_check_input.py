# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the no_raw_sqlite3_check COMPUTE node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelNoRawSqlite3CheckInput"]


class ModelNoRawSqlite3CheckInput(BaseModel):
    """Request to AST-scan a set of (path, source) pairs for raw sqlite3.connect() calls."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)
