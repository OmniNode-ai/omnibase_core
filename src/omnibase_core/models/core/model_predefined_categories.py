"""
Predefined Action Categories.

Contains all predefined action categories that are automatically registered
in the ModelActionCategory registry on import.
"""

from omnibase_core.models.core.model_action_category import ModelActionCategory


def _create_and_register_category(
    name: str,
    display_name: str,
    description: str,
) -> ModelActionCategory:
    """Helper to create and register action categories."""
    category = ModelActionCategory(
        name=name,
        display_name=display_name,
        description=description,
    )
    ModelActionCategory.register(category)
    return category


# Predefined Categories
LIFECYCLE = _create_and_register_category(
    "lifecycle",
    "EnumLifecycle",
    "Node lifecycle management actions (health, initialization, shutdown)",
)

OPERATION = _create_and_register_category(
    "operation",
    "Operation",
    "Core operational actions that process or manipulate data",
)

VALIDATION = _create_and_register_category(
    "validation",
    "Validation",
    "Actions that validate, verify, or check data integrity",
)

MANAGEMENT = _create_and_register_category(
    "management",
    "Management",
    "Administrative actions for configuration and deployment",
)

QUERY = _create_and_register_category(
    "query",
    "Query",
    "Read-only actions that retrieve or monitor data",
)

TRANSFORMATION = _create_and_register_category(
    "transformation",
    "Transformation",
    "Actions that transform data between formats or structures",
)
