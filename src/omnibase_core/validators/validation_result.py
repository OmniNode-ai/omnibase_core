"""
Validation result data structures for circular import detection.

Provides structured result types for import validation operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ImportStatus(Enum):
    """Status of a module import attempt."""

    SUCCESS = "success"
    CIRCULAR_IMPORT = "circular_import"
    IMPORT_ERROR = "import_error"
    UNEXPECTED_ERROR = "unexpected_error"
    SKIPPED = "skipped"


@dataclass
class ModuleImportResult:
    """Result of attempting to import a single module."""

    module_name: str
    status: ImportStatus
    error_message: Optional[str] = None
    file_path: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if import was successful."""
        return self.status == ImportStatus.SUCCESS

    @property
    def has_circular_import(self) -> bool:
        """Check if a circular import was detected."""
        return self.status == ImportStatus.CIRCULAR_IMPORT


@dataclass
class ValidationResult:
    """Overall validation results for circular import detection."""

    total_files: int
    successful_imports: list[ModuleImportResult] = field(default_factory=list)
    circular_imports: list[ModuleImportResult] = field(default_factory=list)
    import_errors: list[ModuleImportResult] = field(default_factory=list)
    unexpected_errors: list[ModuleImportResult] = field(default_factory=list)
    skipped: list[ModuleImportResult] = field(default_factory=list)

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

    def add_result(self, result: ModuleImportResult) -> None:
        """Add a module import result to the appropriate category."""
        if result.status == ImportStatus.SUCCESS:
            self.successful_imports.append(result)
        elif result.status == ImportStatus.CIRCULAR_IMPORT:
            self.circular_imports.append(result)
        elif result.status == ImportStatus.IMPORT_ERROR:
            self.import_errors.append(result)
        elif result.status == ImportStatus.UNEXPECTED_ERROR:
            self.unexpected_errors.append(result)
        elif result.status == ImportStatus.SKIPPED:
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
