from uuid import UUID

from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"\nOrchestrator plan model.\n"
from pydantic import BaseModel

from omnibase_core.models.services.model_custom_fields import ModelCustomFields

from .model_orchestrator_step import ModelOrchestratorStep


class ModelOrchestratorPlan(BaseModel):
    """ONEX plan model for orchestrator."""

    plan_id: UUID = Field(default=..., description="Plan identifier")
    plan_name: str = Field(default=..., description="Plan name")
    steps: list[ModelOrchestratorStep] = Field(
        default_factory=list, description="Plan steps"
    )
    description: str | None = Field(default=None, description="Plan description")
    version: ModelSemVer | None = Field(default=None, description="Plan version")
    created_at: str | None = Field(default=None, description="Plan creation timestamp")
    author: str | None = Field(default=None, description="Plan author")
    custom_metadata: ModelCustomFields | None = Field(
        default=None, description="Custom metadata fields"
    )


__all__ = ["ModelOrchestratorPlan"]
