# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-Ledger Verdict Status Enum (OMN-19405, typed work ledger).

The answer a work-ledger query gives. Every query answers from typed fields
only, and any doubt about the ledger itself answers UNDECIDED, never CLEAR.
The exit codes follow the pause check the skills already use: 0 for CLEAR,
3 for HELD or FOUND, 2 for UNDECIDED.
"""

from enum import StrEnum, unique


@unique
class EnumWorkLedgerVerdictStatus(StrEnum):
    """Outcome of one work-ledger query."""

    CLEAR = "clear"
    """Nothing in force matches the question."""

    HELD = "held"
    """At least one hold in force matches the question."""

    FOUND = "found"
    """At least one open claim or unacknowledged inbox item matches."""

    UNDECIDED = "undecided"
    """The ledger could not be read with certainty; the caller must not proceed."""


__all__: list[str] = ["EnumWorkLedgerVerdictStatus"]
