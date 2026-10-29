# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Source texts supplied to the pure bare-feature-flag validator."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_rules import (
    ModelBareFeatureFlagRules,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelBareFeatureFlagCheckInput(BaseModel):
    """Explicit source texts, without filesystem or bus dependencies."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rules: ModelBareFeatureFlagRules
    files: list[ModelSourceFile] = Field(default_factory=list)
