# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The two phases of the lab-receipt check (OMN-21823)."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumLabReceiptPhase"]


class EnumLabReceiptPhase(StrEnum):
    """Which rows of the lab_receipt contract apply to a run.

    PRESENT judges what a hosted check can read with a repository token. VERIFY
    additionally judges the receipt against lab reads supplied as facts.
    """

    PRESENT = "present"
    VERIFY = "verify"
