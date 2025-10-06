from typing import Dict

"""
TypedDictMigrationDuplicateConflictDict

Type definition for exact duplicate conflict information.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.migration_types (dependency)
"""

from typing import TypedDict

from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict


class TypedDictMigrationDuplicateConflictDict(TypedDictMigrationConflictBaseDict):
    """Type definition for exact duplicate conflict information."""

    signature_hash: str
