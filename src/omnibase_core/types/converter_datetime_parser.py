# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Datetime parsing utilities for TypedDict conversions.

Provides consistent datetime parsing across the codebase. Canonical home
(OMN-14959): relocated from ``omnibase_core.utils.util_datetime_parser`` so
the ``types`` foundation package is self-contained under the
``core-foundation-no-upward`` import-linter contract (OMN-3210) — the only
consumers were the three ``types/converter_*.py`` modules below. The old
``utils`` path is retained as a pure re-export shim for back-compat
(``utils -> types`` is downward-legal and uncontracted).
"""

from __future__ import annotations

from datetime import datetime


def parse_datetime(value: object) -> datetime:
    """Parse a datetime value from various input types."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            # Try ISO format first
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # Fallback to current datetime for invalid strings
            return datetime.now()
    # Default for empty/None values
    return datetime.now()
