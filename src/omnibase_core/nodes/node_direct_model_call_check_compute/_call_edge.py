# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A call from one repository function to another (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _CallEdge:
    caller: tuple[str, str]
    callee: tuple[str, str]
    line: int
