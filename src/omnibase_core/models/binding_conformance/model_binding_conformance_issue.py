# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One reason a checked node does not conform."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_binding_rule import EnumBindingRule


class ModelBindingConformanceIssue(BaseModel):
    """Names the node, the file, the line (0 when the rule has none) and the rule broken."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str
    path: str
    line: int
    rule: EnumBindingRule
    detail: str
