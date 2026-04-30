# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelSemanticDiffReport — aggregate result of an AST semantic diff (OMN-10371)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.analysis.model_symbol_change import ModelSymbolChange


class ModelSemanticDiffReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    changes: tuple[ModelSymbolChange, ...]
    total_consumers_affected: int
