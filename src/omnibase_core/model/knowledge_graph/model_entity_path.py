"""
Entity path model for representing paths between knowledge entities.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.knowledge_graph.model_path_step import ModelPathStep


class ModelEntityPath(BaseModel):
    """Model for paths between knowledge entities."""

    path_id: str = Field(..., description="Unique identifier for the path")
    source_entity_id: str = Field(..., description="Starting entity ID")
    target_entity_id: str = Field(..., description="Ending entity ID")
    steps: list[ModelPathStep] = Field(..., description="Sequence of steps in the path")
    total_length: int = Field(..., description="Total number of hops in path")
    total_weight: float = Field(..., description="Cumulative weight of the path")
    semantic_coherence: float = Field(
        ...,
        description="Semantic coherence score (0.0-1.0)",
    )

    model_config = ConfigDict(frozen=True, validate_assignment=True)
