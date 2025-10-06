from __future__ import annotations

"""
Status Enum Migration Utilities.

Provides utilities for migrating from the old conflicting status enums to the
new unified status hierarchy.

Usage:
    # Migrate enum values
    migrator = EnumStatusMigrator()
    new_status = migrator.migrate_execution_status(old_value)

    # Validate migration
    validator = EnumStatusMigrationValidator()
    issues = validator.validate_model_migration(model_class)
"""


# Import status migration utilities
from omnibase_core.models.core.model_status_migrator import (
    LEGACY_ENUM_STATUS_VALUES,
    LEGACY_EXECUTION_STATUS_VALUES,
    LEGACY_FUNCTION_STATUS_VALUES,
    LEGACY_METADATA_NODE_STATUS_VALUES,
    LEGACY_SCENARIO_STATUS_VALUES,
    ModelEnumStatusMigrator,
)

# Alias for backward compatibility
EnumStatusMigrator = ModelEnumStatusMigrator
from omnibase_core.models.core.model_status_protocol import (
    EnumStatusProtocol,
    StatusEnumType,
)
from omnibase_core.models.core.model_validation_result_status import ValidationResult
from omnibase_core.models.validation.model_status_migration_validator import (
    ModelEnumStatusMigrationValidator,
)

# Alias for backward compatibility
EnumStatusMigrationValidator = ModelEnumStatusMigrationValidator

# Public API exports
__all__ = [
    "LEGACY_ENUM_STATUS_VALUES",
    "LEGACY_EXECUTION_STATUS_VALUES",
    "LEGACY_FUNCTION_STATUS_VALUES",
    "LEGACY_METADATA_NODE_STATUS_VALUES",
    "LEGACY_SCENARIO_STATUS_VALUES",
    "EnumStatusProtocol",
    "StatusEnumType",
    "ValidationResult",
    "EnumStatusMigrator",
    "EnumStatusMigrationValidator",
]
