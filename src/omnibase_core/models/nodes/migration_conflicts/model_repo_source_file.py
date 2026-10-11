# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A source file read from one repository under the repos root."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelRepoSourceFile"]


class ModelRepoSourceFile(BaseModel):
    """A (repository, path, source) triple.

    path is the path as discovered under the repos root. resolved_path
    is that path with symbolic links resolved, the key the migration inventory
    is matched on; it is empty for files the inventory is never matched against.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_name: str
    path: str
    resolved_path: str = ""
    source: str
