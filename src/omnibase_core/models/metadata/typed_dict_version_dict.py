from typing import TypedDict


class TypedDictVersionDict(TypedDict):
    """Version dictionary structure."""

    major: int
    minor: int
    patch: int
