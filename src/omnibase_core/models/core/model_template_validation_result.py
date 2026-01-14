"""Result of template validation with comprehensive metrics"""

from pydantic import BaseModel

from .model_validation_issue import ModelValidationIssue


class ModelTemplateValidationResult(BaseModel):
    """Result of template validation with comprehensive metrics"""

    issues: list[ModelValidationIssue]
    error_level_count: int
    warning_count: int
    info_count: int
    total_files_checked: int
    node_name: str
    validation_passed: bool
