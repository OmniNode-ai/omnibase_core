# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-Outcome Enum (OMN-16177).

The closed set of terminal states a unit of work can be recorded in on a
``work.result.recorded`` event. Distinct from ``EnumProofClass``, which names
*which surface proves* the claim rather than *what happened*.
"""

from enum import StrEnum, unique


@unique
class EnumWorkOutcome(StrEnum):
    """What happened to a unit of work."""

    LANDED = "landed"
    """The work merged and its proof surface was read."""

    BLOCKED = "blocked"
    """Stopped on a named external blocker the actor could not clear."""

    ABANDONED = "abandoned"
    """Deliberately dropped; no successor work item carries it forward."""

    SUPERSEDED = "superseded"
    """Replaced by different work that covers the same ground."""

    TERMINAL = "terminal"
    """The lane reached its end state without landing — reported honestly."""


__all__: list[str] = ["EnumWorkOutcome"]
