# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Quoting and nesting state carried across one check_value scan (OMN-15411)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ShellScanState"]


@dataclass
class ShellScanState:
    """Quoting / nesting state carried across one check_value scan."""

    in_single: bool = False
    in_double: bool = False
    in_backtick: bool = False
    depth: int = 0
