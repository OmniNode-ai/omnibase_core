import uuid
from typing import Any

from pydantic import Field

from omnibase_core.models.core.model_workflow import ModelWorkflow
from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Workflow Instance Model - ONEX Standards Compliant.

Model for workflow execution instances in the ONEX workflow coordination system.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.enums.enum_workflow_coordination import EnumWorkflowStatus

# Type aliases for structured data - ZERO TOLERANCE for Any types
from omnibase_core.types.constraints import PrimitiveValueType

ParameterValue = PrimitiveValueType
StructuredData = dict[str, ParameterValue]


class ModelWorkflowInstance(BaseModel):
    """A workflow execution instance."""

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the workflow instance",
    )

    workflow_name: str = Field(default=..., description="Name of the workflow")

    workflow_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the workflow definition",
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
