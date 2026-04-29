# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLAUDE.md cross-reference check result model."""

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelDocCrossRefCheck(BaseModel):
    """Result of checking a single CLAUDE.md instruction against repo state.

    Used by the CLAUDE.md cross-reference checker to validate that
    instructions (commands, paths, conventions, table entries) match
    the actual state of the repository.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    instruction: str = Field(
        ...,
        description="The CLAUDE.md instruction being checked",
        max_length=_MAX_STRING_LENGTH,
    )
    line_number: int = Field(
        ...,
        description="Line number in the CLAUDE.md file",
        ge=1,
    )
    check_type: str = Field(
        ...,
        description="Type of check: command, path, convention, table",
    )
    verified: bool = Field(
        ...,
        description="Whether the instruction was verified as correct",
    )
    evidence: str = Field(
        ...,
        description="What was checked and what was found",
        max_length=_MAX_STRING_LENGTH,
    )
