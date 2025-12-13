"""
Strongly-typed metadata structures.

Replaces dict[str, Any] usage in metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.

"""

from __future__ import annotations

from .model_event_metadata import ModelEventMetadata

# Import models from individual files following ONEX one-model-per-file architecture
from .model_execution_metadata import ModelExecutionMetadata
from .model_system_metadata import ModelSystemMetadata
from .model_workflow_instance_metadata import ModelWorkflowInstanceMetadata

# Export all models
__all__ = [
    "ModelEventMetadata",
    "ModelExecutionMetadata",
    "ModelSystemMetadata",
    "ModelWorkflowInstanceMetadata",
]
