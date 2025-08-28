from datetime import datetime
from typing import List

from pydantic import BaseModel

from omnibase.enums.enum_log_level import SeverityLevelEnum


class ModelGenerationResult(BaseModel):
    """Result of code generation operations"""

    success: bool
    files_generated: List[str]
    files_modified: List[str]
    errors: List[str]
    warnings: List[str]
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
    def severity(self) -> SeverityLevelEnum:
        """Get overall severity level"""
        if self.has_errors:
            return SeverityLevelEnum.ERROR
        elif self.has_warnings:
            return SeverityLevelEnum.WARNING
        else:
            return SeverityLevelEnum.SUCCESS
