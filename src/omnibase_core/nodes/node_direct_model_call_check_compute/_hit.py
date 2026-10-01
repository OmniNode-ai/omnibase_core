# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One model-call signal found at a sink (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind


@dataclass(frozen=True)
class _Hit:
    kind: EnumDirectModelCallKind
    target: str
    evidence: str
    weak: bool = False
