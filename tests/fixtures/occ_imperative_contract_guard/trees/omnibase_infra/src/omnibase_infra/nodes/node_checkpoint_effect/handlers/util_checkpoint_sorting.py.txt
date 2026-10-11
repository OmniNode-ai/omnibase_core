# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2026 OmniNode Team
"""Shared sorting utilities for checkpoint file discovery.

Extracted from handler_checkpoint_list to avoid cross-module imports of
private helpers.

Ticket: OMN-2143
"""

from __future__ import annotations

from pathlib import Path


def attempt_number(path: Path) -> int:
    """Extract numeric attempt from filename like ``phase_1_implement_a3.yaml``.

    Returns ``0`` when no ``_a<N>`` suffix is found.  This is intentional:
    returning 0 ensures non-attempt-suffixed files sort before any numbered
    attempt, which is the desired ordering for checkpoint discovery.
    """
    stem = path.stem
    after_a = stem.rsplit("_a", maxsplit=1)
    if len(after_a) == 2 and after_a[1].isdigit():
        return int(after_a[1])
    return 0


__all__: list[str] = ["attempt_number"]
