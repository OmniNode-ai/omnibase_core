from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_event_data_base import ModelEventDataBase


class ModelWorkflowEventData(ModelEventDataBase):
    """Workflow execution event data."""

    event_type: Literal[EnumEventType.WORKFLOW] = Field(
        default=EnumEventType.WORKFLOW,
        description="Workflow event type",
    )
    workflow_stage: str = Field(default=..., description="Current workflow stage")
    workflow_step: str = Field(default=..., description="Current workflow step")
    execution_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Workflow execution metrics",
    )
    state_changes: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Workflow state changes",
    )
