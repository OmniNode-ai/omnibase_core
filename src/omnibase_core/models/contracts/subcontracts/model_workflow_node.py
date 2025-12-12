"""
Workflow Node Model.

Model for node definitions in workflow graphs for the ONEX workflow coordination system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Type aliases for structured data - Strict typing is enforced for Any types
from omnibase_core.types.constraints import PrimitiveValueType

ParameterValue = PrimitiveValueType
StructuredData = dict[str, ParameterValue]


class ModelWorkflowNode(BaseModel):
    """A node definition in a workflow graph."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node",
    )

    node_type: EnumNodeType = Field(default=..., description="Type of the node")

    node_requirements: StructuredData = Field(
        default_factory=dict,
        description="Requirements for this node",
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of node IDs this node depends on",
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
