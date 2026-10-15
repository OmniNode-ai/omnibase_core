# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Status vocabulary for context-source results (OMN-18531 / TC.1).

The six values are the status vocabulary of the system-level learning and
execution architecture plan, section 8. A stale projection or an unavailable
service is not evidence that the fact does not exist, so absence is never
reported as ``RESOLVED`` with no entries.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumContextSourceStatus(StrEnum):
    """Outcome of one context-source read, or of one entry within a read."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    STALE = "stale"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"


__all__ = [
    "EnumContextSourceStatus",
]
