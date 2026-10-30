# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure parsing and budget allocation for baselines that follow recorded moves."""

from __future__ import annotations

from collections.abc import Mapping


def parse_name_status_moves(text: str) -> dict[str, str]:
    """Read rename and copy destinations from tab-separated git name-status data."""
    moves: dict[str, str] = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            continue
        status, origin, destination = fields
        if status[:1] in {"R", "C"} and status[1:].isdigit():
            moves.setdefault(destination, origin)
    return moves


def carry_baseline(
    head: Mapping[str, int],
    base: Mapping[str, int],
    moves: Mapping[str, str],
) -> dict[str, int]:
    """Allocate each origin's remaining base budget to sorted moved destinations."""
    allowances: dict[str, int] = {}
    drawn: dict[str, int] = {}
    for path in sorted(head):
        if path in base:
            allowances[path] = base[path]
            continue
        origin = path
        visited: set[str] = set()
        while origin not in base and origin in moves and origin not in visited:
            visited.add(origin)
            origin = moves[origin]
        if origin not in base:
            allowances[path] = 0
            continue
        remaining = max(0, base[origin] - head.get(origin, 0) - drawn.get(origin, 0))
        allowance = min(head[path], remaining)
        allowances[path] = allowance
        drawn[origin] = drawn.get(origin, 0) + allowance
    return allowances


__all__ = ["carry_baseline", "parse_name_status_moves"]
