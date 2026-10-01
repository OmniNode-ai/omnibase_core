# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One direct model call site before it becomes a finding (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.nodes.node_direct_model_call_check_compute._hit import _Hit


@dataclass(frozen=True)
class _Site:
    path: str
    symbol: str
    line: int
    hit: _Hit
