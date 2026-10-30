# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data of the cosmetic lint: which checks run, and the files and markers they read."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCosmeticLintRules"]


class ModelCosmeticLintRules(BaseModel):
    """Read from ``validation/contracts/cosmetic_lint.validation.yaml``; never code.

    ``checks`` are the ids of the enabled rule rows, in the order the checks run and
    report in. Every path is repository-relative.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    checks: tuple[str, ...] = Field(min_length=1)
    spdx_skip_marker: str = Field(min_length=1)
    pyproject_path: str = Field(min_length=1)
    precommit_path: str = Field(min_length=1)
    readme_path: str = Field(min_length=1)
    readme_header_lines: int = Field(ge=0)
    github_directory: str = Field(min_length=1)
