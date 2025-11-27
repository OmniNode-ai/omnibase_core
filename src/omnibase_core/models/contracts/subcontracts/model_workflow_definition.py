from pydantic import Field

"""
Workflow Definition Model - ONEX Standards Compliant.

Model for complete workflow definitions in the ONEX workflow coordination system.
"""

from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_coordination_rules import ModelCoordinationRules
from .model_execution_graph import ModelExecutionGraph
from .model_workflow_definition_metadata import ModelWorkflowDefinitionMetadata


class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_metadata: ModelWorkflowDefinitionMetadata = Field(
        default=...,
        description="Workflow metadata",
    )

    execution_graph: ModelExecutionGraph = Field(
        default=...,
        description="Execution graph for the workflow",
    )

    coordination_rules: ModelCoordinationRules = Field(
        default_factory=lambda: ModelCoordinationRules(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Rules for workflow coordination",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
