# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Source texts and rule data supplied to the pure no-hardcoded-topics check."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_rules import (
    ModelNoHardcodedTopicsRules,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelNoHardcodedTopicsCheckInput(BaseModel):
    """Explicit source texts and the rules to judge them by, without I/O."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)
    rules: ModelNoHardcodedTopicsRules
