"""Message-related factory parameters."""

from __future__ import annotations

from typing import TypedDict

from omnibase_core.enums.enum_severity_level import EnumSeverityLevel


class TypedDictMessageParams(TypedDict, total=False):
    """Message-related factory parameters."""

    message: str
    severity: EnumSeverityLevel


__all__ = ["TypedDictMessageParams"]
