"""
Workflow configuration model to replace Dict[str, Any] usage in workflow configs.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field

from .model_matrix_strategy import ModelMatrixStrategy
from .model_service_container import ModelServiceContainer
from .model_workflow_dispatch import ModelWorkflowDispatch

# Import separated models
from .model_workflow_input import ModelWorkflowInput
from .model_workflow_permissions import ModelWorkflowPermissions
from .model_workflow_services import ModelWorkflowServices
from .model_workflow_strategy import ModelWorkflowStrategy


class ModelWorkflowConfiguration(BaseModel):
    """Structured workflow configuration settings."""

    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable workflow checkpointing",
    )
    checkpoint_interval: int = Field(
        default=10,
        description="Checkpoint interval in steps",
    )
    error_handling_strategy: str = Field(
        default="stop_on_error",
        description="Error handling strategy",
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable workflow monitoring",
    )
    metrics_collection: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    notification_settings: dict[str, str] = Field(
        default_factory=dict,
        description="Notification configuration",
    )
    resource_limits: dict[str, str] = Field(
        default_factory=dict,
        description="Resource limit configuration",
    )


# Compatibility aliases
WorkflowInput = ModelWorkflowInput
WorkflowDispatch = ModelWorkflowDispatch
ServiceContainer = ModelServiceContainer
WorkflowServices = ModelWorkflowServices
MatrixStrategy = ModelMatrixStrategy
WorkflowStrategy = ModelWorkflowStrategy
WorkflowPermissions = ModelWorkflowPermissions

# Re-export
__all__ = [
    "ModelMatrixStrategy",
    "ModelServiceContainer",
    "ModelWorkflowConfiguration",
    "ModelWorkflowDispatch",
    "ModelWorkflowInput",
    "ModelWorkflowPermissions",
    "ModelWorkflowServices",
    "ModelWorkflowStrategy",
]
