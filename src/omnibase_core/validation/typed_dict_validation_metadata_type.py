from typing import Dict

"""
ValidationMetadataType TypedDict

Type-safe validation metadata structure.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from typing import TypedDict


class ValidationMetadataType(TypedDict, total=False):
    """Type-safe validation metadata structure."""

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
