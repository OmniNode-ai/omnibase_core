"""
Job model.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_workflow_configuration import (
    WorkflowServices,
    WorkflowStrategy,
)

from .model_step import ModelStep


class ModelJob(BaseModel):
    """GitHub Actions workflow job."""

    runs_on: str | list[str] = Field(default=..., alias="runs-on")
    steps: list[ModelStep]
    name: str | None = None
    needs: Any = None
    if_: str | None = Field(default=None, alias="if")
    env: dict[str, str] | None = None
    timeout_minutes: int | None = Field(default=None, alias="timeout-minutes")
    strategy: WorkflowStrategy | None = None
    continue_on_error: bool | None = Field(default=None, alias="continue-on-error")
    container: Any = None
    services: WorkflowServices | None = None
    outputs: dict[str, str] | None = None
