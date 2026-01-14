"""
Datetime parsing utilities for TypedDict conversions.

Provides consistent datetime parsing across the codebase.
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
