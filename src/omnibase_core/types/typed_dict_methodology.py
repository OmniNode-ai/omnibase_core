"""TypedDict for methodology configuration."""

from __future__ import annotations

from typing import TypedDict


class TypedDictMethodology(TypedDict, total=False):
    """Methodology configuration for agent philosophy.

    Describes the operational methodology including approach,
    framework, and quality standards.
    """

    approach: str
    framework: str
    quality_standards: str


__all__ = ["TypedDictMethodology"]
