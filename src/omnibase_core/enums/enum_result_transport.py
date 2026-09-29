# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-declared transport for an operation's typed result (OMN-17859)."""

from enum import Enum, unique


@unique
class EnumResultTransport(str, Enum):
    """Select whether an operation result is returned or emitted as events.

    ``RESPONSE`` keeps the typed result on the response path. ``EVENT_FANOUT``
    authorizes the runtime to resolve each returned event through the contract's
    ``published_events`` map. No operation-level topic exists: contracts remain
    the only topic authority.
    """

    RESPONSE = "response"
    EVENT_FANOUT = "event_fanout"


__all__ = ["EnumResultTransport"]
