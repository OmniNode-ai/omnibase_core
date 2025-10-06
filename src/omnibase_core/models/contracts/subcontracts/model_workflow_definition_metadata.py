from pydantic import Field

from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Workflow Metadata Model - ONEX Standards Compliant.

Model for workflow metadata in the ONEX workflow coordination system.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelWorkflowDefinitionMetadata(BaseModel):
    """Metadata for a workflow definition."""

    name: str = Field(default=..., description="Name of the workflow")

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the workflow",
    )

    description: str = Field(default=..., description="Description of the workflow")

    timeout_ms: int = Field(
        default=600000,
        description="Workflow timeout in milliseconds",
        ge=1000,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
