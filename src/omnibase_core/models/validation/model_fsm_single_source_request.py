# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the FSM single-source check: two texts and the rule values (OMN-21513)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_fsm_single_source_rules import (
    ModelFsmSingleSourceRules,
)
from omnibase_core.models.validation.model_fsm_source_text import ModelFsmSourceText

__all__ = ["ModelFsmSingleSourceRequest"]


class ModelFsmSingleSourceRequest(BaseModel):
    """A reducer's contract text, the text of its Python sources and the contract's rule values."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_source: ModelFsmSourceText
    sources: tuple[ModelFsmSourceText, ...]
    rules: ModelFsmSingleSourceRules
