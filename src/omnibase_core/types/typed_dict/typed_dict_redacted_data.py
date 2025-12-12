"""TypedDict for data after redaction processing."""

from __future__ import annotations

from typing import TypedDict


class TypedDictRedactedData(TypedDict):
    """TypedDict for data after redaction processing.

    This is intentionally flexible since redaction can be applied to any structure.
    """


__all__ = ["TypedDictRedactedData"]
