"""Node outputs collection model."""

from pydantic import BaseModel, Field

from .model_node_output_data import ModelNodeOutputData


class ModelNodeOutputs(BaseModel):
    """Collection of node outputs by node ID."""

    outputs: dict[str, ModelNodeOutputData] = Field(
        default_factory=dict,
        description="Node outputs keyed by node ID",
    )
