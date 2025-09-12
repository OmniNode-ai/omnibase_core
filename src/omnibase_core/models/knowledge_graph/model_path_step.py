"""
Path step model for representing individual steps in entity paths.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPathStep(BaseModel):
    """Model for individual steps in knowledge entity paths."""

    from_entity_id: str = Field(..., description="Source entity ID for this step")
    to_entity_id: str = Field(..., description="Target entity ID for this step")
    relationship_id: str = Field(
        ...,
        description="Relationship ID connecting the entities",
    )
    relationship_type: str = Field(..., description="Type of relationship traversed")
    step_weight: float = Field(..., description="Weight of this step")
    step_number: int = Field(..., description="Position in the path sequence")

    model_config = ConfigDict(frozen=True, validate_assignment=True)
