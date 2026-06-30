# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGithubTokenViolation — single raw GitHub-token env read finding (OMN-13310)."""

from __future__ import annotations

__all__ = ["ModelGithubTokenViolation"]

from pydantic import BaseModel, ConfigDict, Field


class ModelGithubTokenViolation(BaseModel):
    """A single raw GitHub-token env read found during scanning.

    Produced by the github-token-env-reads COMPUTE validator (OMN-13310).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    file_path: str = Field(description="Relative or absolute path to the file")
    line_number: int = Field(ge=1, description="1-based line number of the violation")
    detail: str = Field(
        description="Human-readable description of the violation e.g. os.environ[GH_PAT]"  # env-var-ok: documentation string names banned patterns intentionally
    )
    line_text: str = Field(description="The offending source line (stripped)")
