from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_base_result import ModelBaseResult


class ModelWorkflow(BaseModel):
    id: str
    name: str
    category: str
    status: str
    description: Optional[str] = None
    steps: int
    estimated_duration: Optional[str] = None
    last_run: Optional[str] = None


class ModelWorkflowListResult(ModelBaseResult):
    workflows: List[ModelWorkflow] = Field(default_factory=list)
