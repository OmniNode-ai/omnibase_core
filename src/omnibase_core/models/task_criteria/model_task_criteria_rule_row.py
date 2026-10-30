# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One rule row of the task-criteria contract with its validated parameters (OMN-21535)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity


class ModelTaskCriteriaRuleRow(BaseModel):
    """A rule's state, severity, diagnostic text, source selector and parameters."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(description="Whether the rule emits issues")
    severity: EnumSeverity = Field(description="Level of the rule's issues")
    message: str = Field(description="Diagnostic template of the rule")
    source_pattern: str = Field(description="Selects the documents the rule judges")
    texts: dict[str, str] = Field(
        default_factory=dict, description="String parameters by name"
    )
    lists: dict[str, tuple[str, ...]] = Field(
        default_factory=dict, description="List parameters by name"
    )

    def pattern(self, name: str) -> re.Pattern[str]:
        """Compile a string parameter that holds a regular expression."""
        return re.compile(self.texts[name])

    def judges(self, source_name: str) -> bool:
        """Whether the rule's source pattern selects the document."""
        return re.search(self.source_pattern, source_name) is not None
