# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelRuffFinding — a single finding from `ruff check --output-format=json`.

Companion to `ModelMypyFinding`. Not used by the initial ADK eval tracks
(both consume mypy output only) but landed alongside it so the
`models.quality` subtree covers both linters out of the box.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRuffFinding(BaseModel):
    """A single ruff finding."""

    file: str = Field(
        ...,
        min_length=1,
        description="Source-relative path of the file containing the finding.",
    )
    line: int = Field(
        ...,
        ge=1,
        description="1-indexed line number.",
    )
    column: int = Field(
        ...,
        ge=0,
        description="0-indexed column offset.",
    )
    rule: str = Field(
        ...,
        min_length=1,
        description="Ruff rule code (e.g. 'F401', 'E501').",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable message body.",
    )
    fix_available: bool = Field(
        ...,
        description="Whether ruff can autofix this finding.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelRuffFinding"]
