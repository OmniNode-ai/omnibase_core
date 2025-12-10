from __future__ import annotations

"""
TypedDict for security context.
"""


from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictSecurityContext(TypedDict):
    """TypedDict for security context."""

    user_id: UUID
    session_id: UUID
    permissions: list[str]
    roles: list[str]
    authenticated_at: datetime
    expires_at: NotRequired[datetime]


__all__ = ["TypedDictSecurityContext"]
