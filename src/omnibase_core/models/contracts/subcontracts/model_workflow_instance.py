"""
Workflow Instance Model.

Model for workflow execution instances in the ONEX workflow coordination system.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Type aliases for structured data - Strict typing is enforced for Any types
from omnibase_core.types.type_constraints import PrimitiveValueType

ParameterValue = PrimitiveValueType
StructuredData = dict[str, ParameterValue]


class ModelWorkflowInstance(BaseModel):
    """A workflow execution instance."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the workflow instance",
    )

    workflow_name: str = Field(default=..., description="Name of the workflow")

    workflow_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the workflow definition (MUST be provided in YAML contract)",
    )

    created_timestamp: datetime = Field(
        default=...,
        description="When the workflow instance was created",
    )

    status: EnumWorkflowStatus = Field(
        default=...,
        description="Current status of the workflow",
    )

    input_parameters: StructuredData = Field(
        default_factory=dict,
        description="Input parameters for the workflow",
    )

    execution_context: StructuredData = Field(
        default_factory=dict,
        description="Execution context for the workflow",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
