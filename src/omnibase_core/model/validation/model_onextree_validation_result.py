"""
Onextree validation result model.
"""

from enum import Enum

from pydantic import BaseModel

from .model_onextree_tree_node import ModelOnextreeTreeNode
from .model_onextree_validation_error import ModelOnextreeValidationError
from .model_onextree_validation_warning import ModelOnextreeValidationWarning


class ValidationStatusEnum(str, Enum):
    """Validation status enumeration."""

    SUCCESS = "success"
    ERROR = "error"


class ModelOnextreeValidationResult(BaseModel):
    """Onextree validation result model."""

    status: ValidationStatusEnum
    errors: list[ModelOnextreeValidationError] = []
    warnings: list[ModelOnextreeValidationWarning] = []
    summary: str | None = None
    tree: ModelOnextreeTreeNode | None = None
