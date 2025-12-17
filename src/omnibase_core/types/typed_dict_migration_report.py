# ONEX-EXEMPT: typed-dict-collection - Summary TypedDict is nested in main TypedDict
from __future__ import annotations

from typing import TypedDict

"""
TypedDict for ModelEnumStatusMigrationValidator.generate_migration_report() return type.

This module defines the structure returned by the generate_migration_report method,
providing type-safe dictionary representation for migration reports.
"""


class TypedDictMigrationReportSummary(TypedDict):
    """TypedDict for migration report summary section."""

    total_conflicts: int
    conflicting_values: list[str]
    affected_enums: set[str]


class TypedDictMigrationReport(TypedDict):
    """TypedDict for migration report from generate_migration_report().

    Structure matches the return value of
    ModelEnumStatusMigrationValidator.generate_migration_report().
    """

    summary: TypedDictMigrationReportSummary
    conflicts: dict[str, list[str]]
    migration_mapping: dict[str, str]
    recommendations: list[str]


__all__ = [
    "TypedDictMigrationReport",
    "TypedDictMigrationReportSummary",
]
