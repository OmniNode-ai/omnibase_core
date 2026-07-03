# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Append-only violation categories for the OCC append-only gate (OMN-13888)."""

from __future__ import annotations

from enum import StrEnum


class EnumAppendOnlyViolationKind(StrEnum):
    """Category of an OCC append-only violation."""

    ENTRY_EDITED = "entry_edited"
    ENTRY_REMOVED = "entry_removed"
    RECEIPT_FILE_MUTATED = "receipt_file_mutated"


__all__ = ["EnumAppendOnlyViolationKind"]
