from datetime import datetime

from pydantic import BaseModel

from omnibase_core.enums.enum_log_level import EnumLogLevel


class ModelGenerationResult(BaseModel):
    """Result of code generation operations"""

    success: bool
    files_generated: list[str]
    files_modified: list[str]
    errors: list[str]
    warnings: list[str]
    generation_time: datetime
    node_name: str
    operation_type: str  # "introspection", "error_codes", "template_validation", etc.
    total_operations: int

    @property
    def has_errors(self) -> bool:
        """Check if generation had errors"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if generation had warnings"""
        return len(self.warnings) > 0

    @property
    def severity(self) -> EnumLogLevel:
        """Get overall severity level"""
        if self.has_errors:
            return EnumLogLevel.ERROR
        if self.has_warnings:
            return EnumLogLevel.WARNING
        return EnumLogLevel.SUCCESS
