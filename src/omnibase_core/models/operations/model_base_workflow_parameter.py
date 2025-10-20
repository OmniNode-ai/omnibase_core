from pydantic import BaseModel, Field


class ModelBaseWorkflowParameter(BaseModel):
    """Base class for all workflow parameters."""

    name: str = Field(default=..., description="Parameter name")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
