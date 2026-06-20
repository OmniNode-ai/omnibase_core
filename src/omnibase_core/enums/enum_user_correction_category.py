# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""User-correction category enum for the context-selection learning loop.

A user correction is categorized by *what kind* of correction it is. This axis
is orthogonal to ``EnumCorrectionFailureAxis`` (whether the correction counts as
a context-selection failure): both are first-class fields on the correction
event and are never collapsed into a single rolled-up score (OMN-12846).

Lives in ``omnibase_core`` because it crosses the core / omnimarket boundary:
the typed ``ModelUserCorrectionEvent`` in omnimarket references it.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumUserCorrectionCategory(StrEnum):
    """The kind of user correction applied to an agent's work.

    Finite, exhaustive set. Categories are preserved on the event; there is no
    single rolled-up score that flattens them.
    """

    CLARIFICATION = "CLARIFICATION"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    SCOPE_REDUCTION = "SCOPE_REDUCTION"
    SCOPE_EXPANSION = "SCOPE_EXPANSION"
    PRIORITY_SHIFT = "PRIORITY_SHIFT"
    STYLE = "STYLE"
    INTENT = "INTENT"


__all__: list[str] = ["EnumUserCorrectionCategory"]
