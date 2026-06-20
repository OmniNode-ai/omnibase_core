# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Correction failure-axis enum for the context-selection learning loop.

The failure axis is the dimension that decides whether a user correction counts
*against context selection*:

* ``MISUNDERSTANDING`` — context was present at injection but failed to convey
  or disambiguate intent. This is a real context-selection failure and is
  counted toward the context-failure rate.
* ``NEW_INFORMATION`` — a requirement that did not exist at injection time. This
  is NOT a context failure; it is recorded but excluded from the context-failure
  rate.

Orthogonal to ``EnumUserCorrectionCategory`` and stored as a separate
first-class field (OMN-12846). Lives in ``omnibase_core`` because it crosses the
core / omnimarket boundary.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumCorrectionFailureAxis(StrEnum):
    """Whether a user correction counts against context selection."""

    MISUNDERSTANDING = "MISUNDERSTANDING"
    NEW_INFORMATION = "NEW_INFORMATION"


__all__: list[str] = ["EnumCorrectionFailureAxis"]
