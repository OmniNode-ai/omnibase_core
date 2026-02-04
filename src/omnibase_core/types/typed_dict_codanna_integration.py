"""TypedDict for Codanna integration configuration."""

from __future__ import annotations

from typing import TypedDict


class TypedDictCodannaIntegration(TypedDict, total=False):
    """Codanna integration configuration.

    Describes Codanna-specific settings including primary method
    and available capabilities.
    """

    primary_method: str
    capabilities: list[str]


__all__ = ["TypedDictCodannaIntegration"]
