"""
Migration type definitions for protocol migration operations.
"""

# Import all TypedDict classes from types module (ONEX pattern: TypedDicts in types/)
from omnibase_core.types.typed_dict_migration_conflict_base_dict import (
    TypedDictMigrationConflictBaseDict,
)
from omnibase_core.types.typed_dict_migration_duplicate_conflict_dict import (
    TypedDictMigrationDuplicateConflictDict,
)
from omnibase_core.types.typed_dict_migration_name_conflict_dict import (
    TypedDictMigrationNameConflictDict,
)

# Import from types module (ONEX pattern: TypedDicts in types/)
from omnibase_core.types.typed_dict_migration_step_dict import (
    TypedDictMigrationStepDict,
)

# Export all types
__all__ = [
    "TypedDictMigrationConflictBaseDict",
    "TypedDictMigrationDuplicateConflictDict",
    "TypedDictMigrationNameConflictDict",
    "TypedDictMigrationStepDict",
]
