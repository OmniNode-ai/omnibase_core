"""
Onextree validation models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from enum import Enum

from .model_onextree_tree_node import ModelOnextreeTreeNode
from .model_onextree_validation_error import ModelOnextreeValidationError
from .model_onextree_validation_result import (
    ModelOnextreeValidationResult,
    ValidationStatusEnum,
)
from .model_onextree_validation_warning import ModelOnextreeValidationWarning

# Backward compatibility aliases
OnextreeValidationError = ModelOnextreeValidationError
OnextreeValidationWarning = ModelOnextreeValidationWarning
OnextreeTreeNode = ModelOnextreeTreeNode
OnextreeValidationResult = ModelOnextreeValidationResult


class ValidationResultEnum(str, Enum):
    """Validation result enumeration."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


# Re-export for backward compatibility
__all__ = [
    "ModelOnextreeTreeNode",
    "ModelOnextreeValidationError",
    "ModelOnextreeValidationResult",
    "ModelOnextreeValidationWarning",
    "OnextreeTreeNode",
    # Backward compatibility
    "OnextreeValidationError",
    "OnextreeValidationResult",
    "OnextreeValidationWarning",
    "ValidationResultEnum",
    "ValidationStatusEnum",
]

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.711248'
# description: Stamped by ToolPython
# entrypoint: python://model_onextree_validation
# hash: 84f23fd3990b0ff74e47211bb1913de39cd5007c2133888b6b53d9980104a842
# last_modified_at: '2025-05-29T14:13:58.883326+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_onextree_validation.py
# namespace: python://omnibase.model.model_onextree_validation
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 5fedac0f-4389-45c5-9226-999b2ec93d79
# version: 1.0.0
# === /OmniNode:Metadata ===
