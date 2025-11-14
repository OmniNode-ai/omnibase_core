"""
Action Validation System.

Provides validation logic for node actions with strong typing and security checks.
Integrates with node execution pipelines for comprehensive action validation.
"""

from omnibase_core.models.core.model_action_validation_result import (
    ModelActionValidationResult,
)
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.core.model_node_action_validator import (
    ModelNodeActionValidator,
)

# Export the main classes for current standards
ActionValidationResult = ModelActionValidationResult
NodeActionValidator = ModelNodeActionValidator


def create_node_validator(
    node_name: str,
    supported_actions: list[ModelNodeActionType],
    validation_cache_size: int = 100,
) -> ModelNodeActionValidator:
    """
    Create a validator for a specific node.

    Args:
        node_name: Name of the node
        supported_actions: List of rich action types supported by the node
        validation_cache_size: Maximum validation results to cache

    Returns:
        Configured validator instance
    """
    return ModelNodeActionValidator(node_name, supported_actions, validation_cache_size)
