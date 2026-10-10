# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit repository snapshot supplied to the pure cosmetic linter."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_github_snapshot import (
    ModelCosmeticGithubSnapshot,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

__all__ = ["ModelCosmeticLintInput"]


class ModelCosmeticLintInput(BaseModel):
    """What the cosmetic linter decides over, without filesystem or bus access.

    ``None`` for ``pyproject_toml``, ``precommit_config``, ``readme`` or
    ``github`` means the repository has no such file or directory, and the
    matching check reports nothing. ``python_files`` holds the candidate Python
    sources with repository-relative POSIX paths.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    spec_yaml: str
    python_files: list[ModelSourceFile] = Field(default_factory=list)
    pyproject_toml: str | None = None
    precommit_config: str | None = None
    readme: str | None = None
    github: ModelCosmeticGithubSnapshot | None = None
