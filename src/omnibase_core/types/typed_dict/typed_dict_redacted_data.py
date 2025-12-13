"""TypedDict for data after redaction processing."""

from __future__ import annotations

from typing import TypedDict


class TypedDictRedactedData(TypedDict):
    """TypedDict for data after redaction processing.

    Contains metadata about the redaction operation applied to sensitive data.
    """

    redacted: bool
    original_field_count: int
    redacted_field_count: int


__all__ = ["TypedDictRedactedData"]
