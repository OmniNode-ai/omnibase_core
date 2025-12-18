"""
TypedDict for action validation execution context.

Provides typed context for action validation operations including
user identity, permissions, and execution metadata.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class TypedDictActionValidationContext(TypedDict, total=False):
    """TypedDict for action validation execution context.

    Captures execution environment information needed during action validation
    including user identity, permissions, and tracing metadata.

    All fields are optional (total=False) since context may be partial.
    """

    user_id: UUID
    session_id: UUID
    correlation_id: UUID
    permissions: list[str]
    roles: list[str]
    environment: str
    debug_enabled: bool
    trace_enabled: bool


__all__ = ["TypedDictActionValidationContext"]
