# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Question-Withdrawal Reason Enum (OMN-19620, typed work ledger T17).

Why a lane withdrew a question it put to the operator. A withdrawal is never an
answer: only a ruling or consent that names the question answers it. The reason
class says why the question stopped being one, and the withdrawal's evidence
refs say what shows it.
"""

from enum import StrEnum, unique


@unique
class EnumQuestionWithdrawalReason(StrEnum):
    """Why a question was withdrawn by its asker or the lane holding it."""

    OVERTAKEN = "overtaken"
    """Events made the question moot: the work it asked about moved on without it."""

    DUPLICATE = "duplicate"
    """The same question was put elsewhere; the evidence names that question."""

    PREMISE_FALSE = "premise_false"
    """The question rested on a premise that a later read showed to be false."""


__all__: list[str] = ["EnumQuestionWithdrawalReason"]
