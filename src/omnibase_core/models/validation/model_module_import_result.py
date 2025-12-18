"""
Module import result model for circular import detection.

Provides structured result type for individual module import validation attempts.
"""

from dataclasses import dataclass

from omnibase_core.enums.enum_import_status import EnumImportStatus


@dataclass
class ModelModuleImportResult:
    """Result of attempting to import a single module."""

    module_name: str
    status: EnumImportStatus
    error_message: str | None = None
    file_path: str | None = None

    @property
    def is_successful(self) -> bool:
        """Check if import was successful."""
        return self.status == EnumImportStatus.SUCCESS

    @property
    def has_circular_import(self) -> bool:
        """Check if a circular import was detected."""
        return self.status == EnumImportStatus.CIRCULAR_IMPORT


__all__ = ["ModelModuleImportResult"]
