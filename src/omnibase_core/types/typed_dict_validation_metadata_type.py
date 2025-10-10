"""
TypedDict for validation metadata.

Strongly-typed representation for validation metadata structure.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictValidationMetadataType(TypedDict, total=False):
    """Strongly-typed validation metadata structure."""

    protocols_found: int
    recommendations: list[str]
    signature_hashes: list[str]
    file_count: int
    duplication_count: int
    suggestions: list[str]
    total_unions: int
    violations_found: int
    message: str
    validation_type: str
    yaml_files_found: int
    manual_yaml_violations: int
    max_violations: int
    files_with_violations: list[str]
    strict_mode: bool
    error: str
    max_unions: int
    complex_patterns: int


__all__ = ["TypedDictValidationMetadataType"]
