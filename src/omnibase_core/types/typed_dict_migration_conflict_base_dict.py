"""
TypedDict for migration conflict base data.

Strongly-typed representation for base migration conflict information.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictMigrationConflictBaseDict(TypedDict):
    """Strongly-typed base definition for migration conflict information."""

    type: str
    protocol_name: str
    source_file: str
    spi_file: str
    recommendation: str


__all__ = ["TypedDictMigrationConflictBaseDict"]
