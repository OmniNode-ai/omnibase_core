# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Question Status Enum (OMN-19620, typed work ledger T17).

The status the work-ledger fold derives for a question put to the operator.
ANSWERED outranks WITHDRAWN: the operator's word stands, and a withdrawal
recorded beside an answer never changes the status.
"""

from enum import StrEnum, unique


@unique
class EnumQuestionStatus(StrEnum):
    """Where a question put to the operator stands."""

    OPEN = "open"
    """Neither answered nor withdrawn."""

    ANSWERED = "answered"
    """A ruling or consent names the question in its ``answers``."""

    WITHDRAWN = "withdrawn"
    """Not answered, and a valid withdrawal names the question."""


__all__: list[str] = ["EnumQuestionStatus"]
