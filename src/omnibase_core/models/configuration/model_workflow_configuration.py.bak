from typing import Dict

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Workflow configuration model to replace Dict[str, Any] usage in workflow configs.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from typing import Any, Dict

from .model_matrix_strategy import ModelMatrixStrategy
from .model_service_container import ModelServiceContainer
from .model_workflow_dispatch import ModelWorkflowDispatch

# Import separated models
from .model_workflow_input import ModelWorkflowInput
from .model_workflow_permissions import ModelWorkflowPermissions
from .model_workflow_services import ModelWorkflowServices
from .model_workflow_strategy import ModelWorkflowStrategy

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
    "MatrixStrategy",
    "ModelMatrixStrategy",
    "ModelServiceContainer",
    "ModelWorkflowDispatch",
    "ModelWorkflowInput",
    "ModelWorkflowPermissions",
    "ModelWorkflowServices",
    "ModelWorkflowStrategy",
    "ServiceContainer",
    "WorkflowDispatch",
    # Compatibility
    "WorkflowInput",
    "WorkflowPermissions",
    "WorkflowServices",
    "WorkflowStrategy",
]
