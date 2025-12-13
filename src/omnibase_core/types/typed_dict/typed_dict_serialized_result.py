"""TypedDict for serialized execution results."""

from __future__ import annotations

from typing import TypedDict


class TypedDictSerializedResult(TypedDict, total=False):
    """TypedDict for serialized execution results."""

    result: object


__all__ = ["TypedDictSerializedResult"]
