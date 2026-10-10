# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The entries of a repository's ``.github`` directory, supplied to the pure linter."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCosmeticGithubSnapshot"]


class ModelCosmeticGithubSnapshot(BaseModel):
    """Every path under ``.github``, relative to it, as POSIX strings.

    Files and directories both appear (``workflows``, ``workflows/ci.yml``), so
    the linter can answer "does this template exist" and "which files sit
    directly in ``workflows``" without touching the filesystem.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entries: list[str] = Field(default_factory=list)
