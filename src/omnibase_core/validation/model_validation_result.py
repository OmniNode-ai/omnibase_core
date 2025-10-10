"""
ValidationResult

Result of a validation operation.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from dataclasses import dataclass

from omnibase_core.types.typed_dict_validation_metadata_type import (
    ValidationMetadataType,
)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    success: bool
    errors: list[str]
    files_checked: int = 0
    violations_found: int = 0
    files_with_violations: int = 0
    metadata: ValidationMetadataType | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
