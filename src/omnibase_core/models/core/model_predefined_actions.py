"""
Predefined Action Types.

Contains all predefined action types that are automatically registered
in the ModelNodeActionType registry on import.
"""

from typing import Any

from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.core.model_predefined_categories import (
    LIFECYCLE,
    MANAGEMENT,
    OPERATION,
    QUERY,
    TRANSFORMATION,
    VALIDATION,
)


def _create_and_register_action(
    name: str,
    category: ModelActionCategory,
    display_name: str,
    description: str,
    **kwargs: Any,
) -> ModelNodeActionType:
    """Helper to create and register action types."""
    action_type = ModelNodeActionType(
        name=name,
        category=category,
        display_name=display_name,
        description=description,
        **kwargs,
    )
    ModelNodeActionType.register(action_type)
    return action_type


# EnumLifecycle Actions
HEALTH_CHECK = _create_and_register_action(
    "health_check",
    LIFECYCLE,
    "Health Check",
    "Verify node health and readiness",
    estimated_duration_ms=100,
)

INITIALIZE = _create_and_register_action(
    "initialize",
    LIFECYCLE,
    "Initialize",
    "Initialize node for operation",
    estimated_duration_ms=1000,
)

SHUTDOWN = _create_and_register_action(
    "shutdown",
    LIFECYCLE,
    "Shutdown",
    "Gracefully shutdown node",
    is_destructive=True,
    requires_confirmation=True,
    estimated_duration_ms=2000,
)

RESTART = _create_and_register_action(
    "restart",
    LIFECYCLE,
    "Restart",
    "Restart node with current configuration",
    is_destructive=True,
    requires_confirmation=True,
    estimated_duration_ms=3000,
)

STATUS = _create_and_register_action(
    "status",
    LIFECYCLE,
    "Status",
    "Get current node status",
    estimated_duration_ms=50,
)

# Operational Actions
PROCESS = _create_and_register_action(
    "process",
    OPERATION,
    "Process",
    "Process data according to configuration",
    is_destructive=True,
    estimated_duration_ms=5000,
)

EXECUTE = _create_and_register_action(
    "execute",
    OPERATION,
    "Execute",
    "Execute specified operation",
    is_destructive=True,
    estimated_duration_ms=3000,
)

RUN = _create_and_register_action(
    "run",
    OPERATION,
    "Run",
    "Run specified task or workflow",
    estimated_duration_ms=2000,
)

# Data Actions
CREATE = _create_and_register_action(
    "create",
    OPERATION,
    "Create",
    "Create new data or resources",
    is_destructive=True,
    estimated_duration_ms=1000,
)

READ = _create_and_register_action(
    "read",
    QUERY,
    "Read",
    "Read data or resources",
    estimated_duration_ms=500,
)

UPDATE = _create_and_register_action(
    "update",
    OPERATION,
    "Update",
    "Update existing data or resources",
    is_destructive=True,
    estimated_duration_ms=1500,
)

DELETE = _create_and_register_action(
    "delete",
    OPERATION,
    "Delete",
    "Delete data or resources",
    is_destructive=True,
    requires_confirmation=True,
    security_level="elevated",
    estimated_duration_ms=2000,
)

# Validation Actions
VALIDATE = _create_and_register_action(
    "validate",
    VALIDATION,
    "Validate",
    "Validate data against rules or schema",
    estimated_duration_ms=800,
)

VERIFY = _create_and_register_action(
    "verify",
    VALIDATION,
    "Verify",
    "Verify data integrity or correctness",
    estimated_duration_ms=600,
)

CHECK = _create_and_register_action(
    "check",
    VALIDATION,
    "Check",
    "Perform validation checks",
    estimated_duration_ms=400,
)

# Management Actions
CONFIGURE = _create_and_register_action(
    "configure",
    MANAGEMENT,
    "Configure",
    "Configure node settings",
    is_destructive=True,
    requires_confirmation=True,
    security_level="elevated",
    estimated_duration_ms=2000,
)

DEPLOY = _create_and_register_action(
    "deploy",
    MANAGEMENT,
    "Deploy",
    "Deploy resources or configurations",
    is_destructive=True,
    requires_confirmation=True,
    security_level="elevated",
    estimated_duration_ms=10000,
)

BACKUP = _create_and_register_action(
    "backup",
    MANAGEMENT,
    "Backup",
    "Create backup of data or configuration",
    estimated_duration_ms=5000,
)

# Transformation Actions
TRANSFORM = _create_and_register_action(
    "transform",
    TRANSFORMATION,
    "Transform",
    "Transform data from one format to another",
    estimated_duration_ms=3000,
)

CONVERT = _create_and_register_action(
    "convert",
    TRANSFORMATION,
    "Convert",
    "Convert data format or structure",
    estimated_duration_ms=2000,
)

GENERATE = _create_and_register_action(
    "generate",
    TRANSFORMATION,
    "Generate",
    "Generate new content or artifacts",
    estimated_duration_ms=4000,
)

# Monitoring Actions
MONITOR = _create_and_register_action(
    "monitor",
    QUERY,
    "Monitor",
    "Monitor system or process status",
    estimated_duration_ms=200,
)

COLLECT = _create_and_register_action(
    "collect",
    QUERY,
    "Collect",
    "Collect metrics or data points",
    estimated_duration_ms=300,
)

REPORT = _create_and_register_action(
    "report",
    QUERY,
    "Report",
    "Generate status or analytics report",
    estimated_duration_ms=1000,
)
