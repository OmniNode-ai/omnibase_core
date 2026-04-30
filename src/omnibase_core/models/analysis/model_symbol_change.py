# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelSymbolChange — a single symbol-level change in an AST diff (OMN-10371)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_diff_severity import EnumChangeKind, EnumDiffSeverity


class ModelSymbolChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: EnumChangeKind
    severity: EnumDiffSeverity
    symbol_name: str
    file_path: str
    consumers_count: int
