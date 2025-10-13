import uuid

from pydantic import Field

"""
Node Progress Model - ONEX Standards Compliant.

Model for progress information for individual nodes in the ONEX workflow coordination system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.enums.enum_node_type import EnumNodeType


class ModelNodeProgress(BaseModel):
    """Progress information for a single node."""

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node",
    )

    node_type: EnumNodeType = Field(default=..., description="Type of the node")

    progress_percent: float = Field(
        default=...,
        description="Progress percentage for this node",
        ge=0.0,
        le=100.0,
    )

    status: str = Field(default=..., description="Current status of the node")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
