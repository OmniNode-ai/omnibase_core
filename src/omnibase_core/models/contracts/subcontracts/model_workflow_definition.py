from pydantic import Field

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Workflow Definition Model - ONEX Standards Compliant.

Model for complete workflow definitions in the ONEX workflow coordination system.
"""

from pydantic import BaseModel

from .model_coordination_rules import ModelCoordinationRules
from .model_execution_graph import ModelExecutionGraph
from .model_workflow_definition_metadata import ModelWorkflowDefinitionMetadata


class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    workflow_metadata: ModelWorkflowDefinitionMetadata = Field(
        default=...,
        description="Workflow metadata",
    )

    execution_graph: ModelExecutionGraph = Field(
        default=...,
        description="Execution graph for the workflow",
    )

    coordination_rules: ModelCoordinationRules = Field(
        default_factory=ModelCoordinationRules,
        description="Rules for workflow coordination",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
