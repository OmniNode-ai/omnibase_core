"""
Strongly-typed workflow payload structure.

Replaces dict[str, Any] usage in workflow payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelWorkflowPayload(BaseModel):
    """
    Strongly-typed workflow payload.

    Replaces dict[str, Any] with structured workflow payload model.
    """

    workflow_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Workflow data with proper typing"
    )
    input_parameters: dict[str, str] = Field(
        default_factory=dict, description="String input parameters"
    )
    configuration: dict[str, str] = Field(
        default_factory=dict, description="Workflow configuration settings"
    )
    execution_context: dict[str, str] = Field(
        default_factory=dict, description="Execution context information"
    )
    state_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Workflow state data with proper typing"
    )


# Export for use
__all__ = ["ModelWorkflowPayload"]
