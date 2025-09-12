# Model for execution metadata
# DO NOT EDIT MANUALLY - regenerate using model generation tools


from pydantic import BaseModel, Field


class ModelExecutionMetadata(BaseModel):
    """Model for execution metadata."""

    execution_id: str = Field(..., description="Unique execution identifier")
    node_id: str = Field(..., description="Node identifier")
    timestamp: str = Field(..., description="Execution timestamp")
    environment: str = Field(default="production", description="Execution environment")
    tags: list[str] = Field(default_factory=list, description="Execution tags")
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for tracing",
    )
