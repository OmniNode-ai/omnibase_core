# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Supersession status of a context entry (OMN-18531 / TC.1)."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumContextSupersessionStatus(StrEnum):
    """Whether the text an entry carries is still in effect.

    ``UNKNOWN`` is the honest default for a source that does not track
    supersession; it is never read as ``ACTIVE``.
    """

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    AMENDED = "amended"
    CORRECTED = "corrected"
    UNKNOWN = "unknown"


__all__ = [
    "EnumContextSupersessionStatus",
]
