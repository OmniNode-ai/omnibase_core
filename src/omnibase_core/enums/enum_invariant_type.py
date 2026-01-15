"""
Invariant type enumeration for user-defined validation rules.

Invariants are validation rules that ensure AI model changes are safe
before production deployment.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumInvariantType(StrValueHelper, str, Enum):
    """Types of invariant validation rules for AI model safety checks."""

    SCHEMA = "schema"
    """JSON schema validation."""

    FIELD_PRESENCE = "field_presence"
    """Required field paths validation."""

    FIELD_VALUE = "field_value"
    """Field path + expected value/pattern validation."""

    THRESHOLD = "threshold"
    """Metric name + min/max bounds validation."""

    LATENCY = "latency"
    """Maximum latency in milliseconds validation."""

    COST = "cost"
    """Maximum cost per request/token validation."""

    CUSTOM = "custom"
    """Python callable path for custom validation."""


__all__ = ["EnumInvariantType"]
