from typing import Any

from pydantic import Field

"""
Orchestrator plan model.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields

from .model_orchestrator_step import ModelOrchestratorStep


class ModelOrchestratorPlan(BaseModel):
    """ONEX plan model for orchestrator."""

    # Plan identification
    plan_id: str = Field(default=..., description="Plan identifier")
    plan_name: str = Field(default=..., description="Plan name")

    # Plan structure
    steps: list[ModelOrchestratorStep] = Field(
        default_factory=list,
        description="Plan steps",
    )

    # Plan metadata using structured fields
    description: str | None = Field(default=None, description="Plan description")
    version: str | None = Field(default=None, description="Plan version")
    created_at: str | None = Field(default=None, description="Plan creation timestamp")
    author: str | None = Field(default=None, description="Plan author")

    # Custom metadata for extensibility
    custom_metadata: ModelCustomFields | None = Field(
        default=None,
        description="Custom metadata fields",
    )
