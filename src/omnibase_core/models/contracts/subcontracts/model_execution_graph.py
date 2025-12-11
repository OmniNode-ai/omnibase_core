"""
Execution Graph Model.

Model for execution graphs in workflows for the ONEX workflow coordination system.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_workflow_node import ModelWorkflowNode


class ModelExecutionGraph(BaseModel):
    """Execution graph for a workflow."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    nodes: list[ModelWorkflowNode] = Field(
        default_factory=list,
        description="Nodes in the execution graph",
    )

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
        "frozen": True,
        # from_attributes=True allows Pydantic to accept objects with matching
        # attributes even when class identity differs (e.g., in pytest-xdist
        # parallel execution where model classes are imported in separate workers)
        "from_attributes": True,
    }
