# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAislopRule — a single configurable aislop detection rule (OMN-11132)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelAislopRule(BaseModel):
    """A single aislop detection rule."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Unique rule identifier, e.g. 'sycophancy'")
    severity: Literal["ERROR", "WARNING", "INFO"] = Field(
        description="Violation severity"
    )
    enabled: bool = Field(default=True, description="Whether the rule is active")
    pattern_type: Literal[
        "regex_line", "regex_ast_docstring", "grep_code", "ast_check"
    ] = Field(description="How the pattern is matched")
    pattern: str = Field(description="Regex string or AST check identifier")
    file_globs: list[str] = Field(
        default_factory=lambda: ["*.py"],
        description="File glob patterns this rule applies to",
    )
    suppression_annotation: str = Field(
        default="ai-slop-ok",
        description="Inline comment suffix that suppresses this rule",
    )
    description: str = Field(description="Human-readable explanation of the rule")


__all__ = ["ModelAislopRule"]
