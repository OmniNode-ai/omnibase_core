# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Disposition of a view-document section (OMN-21997)."""

from enum import StrEnum

__all__ = ["EnumViewDisposition"]


class EnumViewDisposition(StrEnum):
    """Whether a section holds rows or a typed empty state."""

    POPULATED = "populated"
    """The section carries rows."""

    EMPTY = "empty"
    """The section carries a typed empty state and no rows."""
