# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cost-Basis Enum (OMN-16177, typed work ledger).

Whether a cost recorded on a work event (``work.friction.recorded``) was
measured or estimated. A measured number and an estimate are not the same
claim, and a reader that sums costs must be able to tell them apart.
"""

from enum import StrEnum, unique


@unique
class EnumCostBasis(StrEnum):
    """How a recorded cost was arrived at."""

    MEASURED = "measured"
    """Read from a clock, a run log or a receipt."""

    ESTIMATED = "estimated"
    """A judgement, not a reading."""


__all__: list[str] = ["EnumCostBasis"]
