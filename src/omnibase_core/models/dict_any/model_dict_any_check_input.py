# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the dict[str, Any] detector."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.dict_any.model_dict_any_rules import ModelDictAnyRules
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelDictAnyCheckInput"]


class ModelDictAnyCheckInput(BaseModel):
    """Explicit (path, source) pairs plus the rule data; the handler reads nothing."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[ModelSourceFile, ...]
    rules: ModelDictAnyRules
