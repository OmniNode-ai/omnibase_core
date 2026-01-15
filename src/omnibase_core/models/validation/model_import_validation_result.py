"""
Validation result model for circular import detection.

Provides comprehensive validation results and statistics for module import
validation operations. This is a dataclass (not Pydantic) used specifically
for import validation tooling that detects circular dependencies.

Note: This module defines ModelImportValidationResult (renamed from the
generic ModelValidationResult to avoid naming collision with the common
ModelValidationResult[T] in models/common/model_validation_result.py).
This class specifically aggregates results from circular import detection runs,
tracking successful imports, circular imports, and various error categories.
"""

from dataclasses import dataclass, field

from omnibase_core.enums.enum_import_status import EnumImportStatus
from omnibase_core.models.validation.model_module_import_result import (
    ModelModuleImportResult,
)


@dataclass
class ModelImportValidationResult:
    """
    Overall validation results for circular import detection.

    Aggregates ModelModuleImportResult instances from import validation runs,
    categorizing them by status (success, circular import, error, skipped).
    Used by import validation tooling to detect and report circular dependencies.

    Note:
        This class was renamed from ModelValidationResult to avoid naming
        collision with the generic ModelValidationResult[T] used for general
        validation operations across the codebase.
    """

    total_files: int
    successful_imports: list[ModelModuleImportResult] = field(default_factory=list)
    circular_imports: list[ModelModuleImportResult] = field(default_factory=list)
    import_errors: list[ModelModuleImportResult] = field(default_factory=list)
    unexpected_errors: list[ModelModuleImportResult] = field(default_factory=list)
    skipped: list[ModelModuleImportResult] = field(default_factory=list)

    @property
    def has_circular_imports(self) -> bool:
        """Check if any circular imports were detected."""
        return len(self.circular_imports) > 0

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred (circular imports or other)."""
        return len(self.circular_imports) > 0 or len(self.import_errors) > 0

    @property
    def success_count(self) -> int:
        """Number of successful imports."""
        return len(self.successful_imports)

    @property
    def failure_count(self) -> int:
        """Number of failed imports (all types)."""
        return (
            len(self.circular_imports)
            + len(self.import_errors)
            + len(self.unexpected_errors)
        )

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)."""
        if self.total_files == 0:
            return 0.0
        return (self.success_count / self.total_files) * 100

    def add_result(self, result: ModelModuleImportResult) -> None:
        """Add a module import result to the appropriate category."""
        if result.status == EnumImportStatus.SUCCESS:
            self.successful_imports.append(result)
        elif result.status == EnumImportStatus.CIRCULAR_IMPORT:
            self.circular_imports.append(result)
        elif result.status == EnumImportStatus.IMPORT_ERROR:
            self.import_errors.append(result)
        elif result.status == EnumImportStatus.UNEXPECTED_ERROR:
            self.unexpected_errors.append(result)
        elif result.status == EnumImportStatus.SKIPPED:
            self.skipped.append(result)

    def get_summary(self) -> dict[str, int]:
        """Get a summary of validation results."""
        return {
            "total_files": self.total_files,
            "successful": self.success_count,
            "circular_imports": len(self.circular_imports),
            "import_errors": len(self.import_errors),
            "unexpected_errors": len(self.unexpected_errors),
            "skipped": len(self.skipped),
        }


__all__ = ["ModelImportValidationResult"]
