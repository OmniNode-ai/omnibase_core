# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The unit a sprint's capacity is measured in (OMN-20396).

Tickets is the default and the honest one. Most tickets in the OMN workspace carry no
estimate -- 21 of the 56 open on 2026-10-02 -- so a points cap is part measurement and
part imputation, and the imputed share is large enough to move the answer. A ticket
count is the same number however the estimates are later filled in.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["EnumCapacityUnit"]


class EnumCapacityUnit(str, Enum):
    """How much of a sprint one ticket consumes."""

    TICKETS = "tickets"
    POINTS = "points"
