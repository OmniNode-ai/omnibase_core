# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Commit level for UI action-gate policy decisions (OMN-13131, ADR D2).

Classifies the durability of the effect a declared UI action commits when it
emits its canonical command envelope onto the bus. Distinct from ``reversible``
(a boolean fast-path) in that it expresses the commit axis as a typed ordinal —
read-only actions never mutate truth, reversible actions can be undone, and
irreversible actions cannot. Consumed by the action-gate policy to drive
disabled states, confirmation requirements, and evidence requirements.
"""

from enum import StrEnum


class EnumCommitLevel(StrEnum):
    """Durability of the effect a UI action commits, lowest to highest."""

    READ_ONLY = "read_only"
    """Read-only — emits no truth-mutating command; no commit."""

    REVERSIBLE = "reversible"
    """Reversible — commits an effect that can be undone."""

    IRREVERSIBLE = "irreversible"
    """Irreversible — commits an effect that cannot be undone."""


__all__: list[str] = ["EnumCommitLevel"]
