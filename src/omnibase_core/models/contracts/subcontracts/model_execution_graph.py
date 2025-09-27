"""
Execution Graph Model - ONEX Standards Compliant.

Model for execution graphs in workflows for the ONEX workflow coordination system.
"""

from pydantic import BaseModel, Field

from .model_workflow_node import ModelWorkflowNode


class ModelExecutionGraph(BaseModel):
    """Execution graph for a workflow."""

    nodes: list[ModelWorkflowNode] = Field(
        default_factory=list, description="Nodes in the execution graph"
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
