"""
Orchestrator plan model.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields

from .model_orchestrator_step import ModelOrchestratorStep


class ModelOrchestratorPlan(BaseModel):
    """ONEX plan model for orchestrator."""

    # Plan identification
    plan_id: str = Field(..., description="Plan identifier")
    plan_name: str = Field(..., description="Plan name")

    # Plan structure
    steps: list[ModelOrchestratorStep] = Field(
        default_factory=list,
        description="Plan steps",
    )

    # Plan metadata using structured fields
    description: str | None = Field(None, description="Plan description")
    version: str | None = Field(None, description="Plan version")
    created_at: str | None = Field(None, description="Plan creation timestamp")
    author: str | None = Field(None, description="Plan author")

    # Custom metadata for extensibility
    custom_metadata: ModelCustomFields | None = Field(
        None,
        description="Custom metadata fields",
    )
