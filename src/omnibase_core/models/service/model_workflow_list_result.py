from typing import Any, List

from pydantic import BaseModel, Field


from omnibase_core.models.core.model_workflow import ModelWorkflow

from .model_workflowlistresult import ModelWorkflowListResult


class ModelWorkflow(BaseModel):
    id: str
    name: str
    category: str
    status: str
    description: str | None = None
    steps: int
    estimated_duration: str | None = None
    last_run: str | None = None
