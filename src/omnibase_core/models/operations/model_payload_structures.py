"""
Strongly-typed payload structures.

Replaces dict[str, Any] usage in payloads and message data with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from .model_event_payload import ModelEventPayload

# Import models from individual files following ONEX one-model-per-file architecture
from .model_message_payload import ModelMessagePayload
from .model_operation_payload import ModelOperationPayload
from .model_workflow_payload import ModelWorkflowPayload

# Export all models
__all__ = [
    "ModelEventPayload",
    "ModelMessagePayload",
    "ModelOperationPayload",
    "ModelWorkflowPayload",
]
