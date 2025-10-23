"""
TypedDict for model capability factory parameters.

This provides type-safe parameters for capability factory pattern
without circular import dependencies.
"""

from typing import Any

from typing_extensions import TypedDict


class TypedDictCapabilityFactoryKwargs(TypedDict, total=False):
    """Typed dict[str, Any]ionary for model capability factory parameters."""

    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool
    enabled: bool
