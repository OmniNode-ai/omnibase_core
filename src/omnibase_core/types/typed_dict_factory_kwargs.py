"""
Typed dictionary for factory method parameters.

Provides structured parameter types for model factory operations.
Restructured using composition to reduce string field count and follow ONEX one-model-per-file pattern.
"""

from __future__ import annotations

from typing import Any, TypedDict

from omnibase_core.core.type_constraints import (
    Configurable,
    Nameable,
    ProtocolValidatable,
    Serializable,
)
from omnibase_core.enums.enum_severity_level import EnumSeverityLevel


# Structured TypedDicts to reduce string field violations
class TypedDictExecutionParams(TypedDict, total=False):
    """Execution-related factory parameters.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    success: bool
    exit_code: int
    error_message: str
    data: object  # ONEX compliance - use object instead of Any for generic data


class TypedDictMetadataParams(TypedDict, total=False):
    """Metadata-related factory parameters."""

    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool


class TypedDictMessageParams(TypedDict, total=False):
    """Message-related factory parameters."""

    message: str
    severity: EnumSeverityLevel


# Main factory kwargs that combines sub-groups
class TypedDictFactoryKwargs(
    TypedDictExecutionParams,
    TypedDictMetadataParams,
    TypedDictMessageParams,
    total=False,
):
    """
    Typed dictionary for factory method parameters.

    Restructured using composition to reduce string field count.
    Follows ONEX one-model-per-file architecture pattern.
    """


__all__ = [
    "TypedDictFactoryKwargs",
    "TypedDictExecutionParams",
    "TypedDictMessageParams",
    "TypedDictMetadataParams",
]
