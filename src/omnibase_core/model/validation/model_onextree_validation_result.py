"""
Onextree validation result model.
"""

from enum import Enum
from typing import List, Optional

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
    errors: List[ModelOnextreeValidationError] = []
    warnings: List[ModelOnextreeValidationWarning] = []
    summary: Optional[str] = None
    tree: Optional[ModelOnextreeTreeNode] = None
