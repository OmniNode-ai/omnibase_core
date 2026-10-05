# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Source content and resolved rule configuration for AI-slop validation."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule


class ModelAiSlopCheckInput(BaseModel):
    """Carry all content and rules into the pure checker.

    The script retries docstring rules against the current working directory
    when the configured set has no enabled docstring rules. That independently
    resolved set is carried explicitly in ``fallback_docstring_rules``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)
    rules: list[ModelAislopRule]
    fallback_docstring_rules: list[ModelAislopRule] = Field(default_factory=list)
    strict: bool = False
    report: bool = False
