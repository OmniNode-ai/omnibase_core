"""Model validation demo models for support ticket classification.

This module provides sample input/output models for demonstrating
ONEX model validation capabilities without external dependencies.
"""

from omnibase_core.models.demo.model_validate.model_support_classification import (
    ModelSupportClassificationResult,
)
from omnibase_core.models.demo.model_validate.model_support_ticket import (
    ModelSupportTicket,
)

__all__ = ["ModelSupportTicket", "ModelSupportClassificationResult"]
