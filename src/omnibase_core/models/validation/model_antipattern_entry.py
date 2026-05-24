# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAntipatternEntry — single antipattern detection rule (OMN-11910)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.validation.model_antipattern_example import (
    ModelAntipatternExample,
)


class ModelAntipatternEntry(BaseModel):
    """A single antipattern detection rule with enforcement metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(description="Unique antipattern identifier")
    severity: Literal["ERROR", "WARNING", "INFO"] = Field(
        description="Violation severity"
    )
    enforcement: Literal["blocking", "advisory", "informational"] = Field(
        description="Enforcement level: blocking=merge gate, advisory=warning, informational=log only"
    )
    category: Literal[
        "code_quality", "architecture", "security", "performance", "naming", "testing"
    ] = Field(description="Antipattern category")
    pattern_type: Literal[
        "regex_line", "regex_ast_docstring", "grep_code", "ast_check", "semantic"
    ] = Field(description="How the pattern is matched")
    pattern: str = Field(
        description="Regex string, AST check identifier, or semantic description"
    )
    file_globs: tuple[str, ...] = Field(
        default=("*.py",),
        description="File glob patterns this entry applies to",
    )
    suppression_annotation: str = Field(
        default="antipattern-ok",
        description="Inline comment suffix that suppresses this entry",
    )
    description: str = Field(description="Human-readable explanation")
    rationale: str = Field(description="Why this is an antipattern")
    examples: tuple[ModelAntipatternExample, ...] = Field(
        default=(),
        description="Good and bad code snippet examples",
    )
    discovered_date: date = Field(
        description="Date this antipattern was added to the registry"
    )
    source_ticket: str = Field(
        description="Linear ticket that introduced this entry, e.g. OMN-XXXX"
    )
    vector_enabled: bool = Field(
        default=False,
        description="Whether this entry participates in vector-similarity search",
    )

    @model_validator(mode="after")
    def _validate_semantic_requires_vector_enabled(self) -> ModelAntipatternEntry:
        """semantic pattern_type entries must have vector_enabled=True."""
        if self.pattern_type == "semantic" and not self.vector_enabled:
            raise ValueError("pattern_type='semantic' requires vector_enabled=True")
        return self


__all__ = ["ModelAntipatternEntry"]
