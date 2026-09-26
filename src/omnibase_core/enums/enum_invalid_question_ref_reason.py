# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Invalid Question-Reference Reason Enum (OMN-19620, typed work ledger T17).

Why the work-ledger fold refused an answer or a withdrawal's reference to a
question. A refused reference answers or withdraws nothing, and it is listed
for a human, as a refused hold release is.
"""

from enum import StrEnum, unique


@unique
class EnumInvalidQuestionRefReason(StrEnum):
    """Why an answer or withdrawal reference to a question was refused."""

    UNKNOWN_QUESTION = "unknown_question"
    """The reference names an event_id that is not in the ledger."""

    NOT_A_QUESTION = "not_a_question"
    """The reference names an event that is not a ``work.question.asked``."""


__all__: list[str] = ["EnumInvalidQuestionRefReason"]
