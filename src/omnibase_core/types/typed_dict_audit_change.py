"""TypedDict for audit field changes."""

from typing import TypedDict


class TypedDictAuditChange(TypedDict):
    """Type-safe representation of an audit field change."""

    old: object
    new: object
