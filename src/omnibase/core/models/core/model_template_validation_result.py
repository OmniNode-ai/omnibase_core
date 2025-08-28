"""Result of template validation with comprehensive metrics"""

from typing import List

from pydantic import BaseModel

from .model_validation_issue import ModelValidationIssue


class ModelTemplateValidationResult(BaseModel):
    """Result of template validation with comprehensive metrics"""

    issues: List[ModelValidationIssue]
    error_count: int
    warning_count: int
    info_count: int
    total_files_checked: int
    node_name: str
    validation_passed: bool
