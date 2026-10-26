# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-Ledger Relation Enum (OMN-21107, ruling relationships).

The typed relationship one work event declares about an earlier one: a ruling
or consent that supersedes, amends or extends an earlier ruling or consent, or
a correction naming the record it concerns. Only SUPERSEDES closes what it
names; the rest record a link and leave the target open.
"""

from enum import StrEnum, unique


@unique
class EnumWorkLedgerRelation(StrEnum):
    """How one work event relates to the earlier event it names."""

    SUPERSEDES = "supersedes"
    """Replaces its target entirely; the target's ruling state is no longer open."""

    AMENDS = "amends"
    """Refines its target without replacing it; the target stays open."""

    EXTENDS = "extends"
    """Adds to its target without replacing it; the target stays open."""

    CORRECTS = "corrects"
    """Names the record a correction concerns, of any kind. Never closes it."""


__all__: list[str] = ["EnumWorkLedgerRelation"]
