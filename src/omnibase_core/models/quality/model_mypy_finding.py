# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelMypyFinding — a single typed finding from `mypy --strict`.

Schema for the parsed output of mypy, produced by the shared mypy parser
(`omnimarket/experiments/adk_eval/tools/mypy_parser.py`). Consumed by both
Track A (ADK agent) and Track B (omnimarket POC handler) in the ADK evaluation
spike.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_lint_severity import EnumLintSeverity


class ModelMypyFinding(BaseModel):
    """A single mypy finding (one line of mypy --strict output)."""

    file: str = Field(
        ...,
        min_length=1,
        description="Source-relative path of the file containing the finding.",
    )
    line: int = Field(
        ...,
        ge=1,
        description="1-indexed line number of the finding.",
    )
    column: int | None = Field(
        default=None,
        ge=0,
        description="0-indexed column offset (None if mypy did not report one).",
    )
    severity: EnumLintSeverity = Field(
        ...,
        description="Severity tag reported by mypy ('error' | 'note' | 'warning').",
    )
    error_code: str = Field(
        ...,
        min_length=1,
        description="Mypy error code (e.g. 'no-untyped-def', 'arg-type').",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable message body.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelMypyFinding"]
