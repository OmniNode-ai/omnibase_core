# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeRuleSet -- the loaded contract: parameters, enablement, severity (OMN-21515)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_canonical_file_shape_rules import (
    ModelCanonicalFileShapeRules,
)


class ModelCanonicalFileShapeRuleSet(BaseModel):
    """Rule parameters plus the rule ids the contract enables, with severities."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    parameters: ModelCanonicalFileShapeRules
    enabled: frozenset[str]
    severities: dict[str, str]
