from pydantic import BaseModel, Field

from omnibase_core.models.core.model_base_result import ModelBaseResult


class ModelWorkflow(BaseModel):
    id: str
    name: str
    category: str
    status: str
    description: str | None = None
    steps: int
    estimated_duration: str | None = None
    last_run: str | None = None


class ModelWorkflowListResult(ModelBaseResult):
    workflows: list[ModelWorkflow] = Field(default_factory=list)
