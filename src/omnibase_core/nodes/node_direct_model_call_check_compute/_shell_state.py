# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shell syntax that spans lines: a case statement and a heredoc body (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _ShellState:
    """Shell syntax that spans lines: a case statement and a heredoc body."""

    in_case: bool = False
    expecting_pattern: bool = False
    heredoc: str | None = None
