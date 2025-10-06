from typing import Dict

"""
TypedDictMigrationConflictBaseDict

Base type definition for migration conflict information.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from typing import TypedDict


class TypedDictMigrationConflictBaseDict(TypedDict):
    """Base type definition for migration conflict information."""

    type: str
    protocol_name: str
    source_file: str
    spi_file: str
    recommendation: str
