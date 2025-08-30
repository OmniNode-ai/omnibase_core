"""
OnextreeTreeNode model.
"""

from pydantic import BaseModel, ConfigDict


class ModelOnextreeTreeNode(BaseModel):
    """Onextree tree node model."""

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    name: str
    type: str  # "file" or "directory"
    children: list["ModelOnextreeTreeNode"] | None = None


# Use model_rebuild for forward references in Pydantic v2
ModelOnextreeTreeNode.model_rebuild()
