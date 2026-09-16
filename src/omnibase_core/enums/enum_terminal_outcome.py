# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The outcome a contract declares one of its terminal topics to carry."""

from __future__ import annotations

from enum import Enum, unique

__all__ = ["EnumTerminalOutcome"]


@unique
class EnumTerminalOutcome(str, Enum):
    """What a contract says arriving on a given terminal topic means.

    This is a property of the CONTRACT's declaration, not of any one message.
    A contract that declares ``runtime_dispatch.terminal_events.failure`` has
    stated that everything published there is a failure terminal, so a record
    delivered on it is a failure whatever its payload happens to self-report.

    Values:
        SUCCESS: the topic the contract names as its completed terminal.
        FAILURE: the topic the contract names as its failed terminal.
        UNSPECIFIED: declared terminal, no outcome stated — the payload's own
            declarations decide, exactly as they did before this enum existed.
    """

    SUCCESS = "success"
    FAILURE = "failure"
    UNSPECIFIED = "unspecified"
