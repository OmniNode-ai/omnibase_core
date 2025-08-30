"""
Job model.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omnibase_core.model.configuration.model_workflow_configuration import (
    WorkflowServices, WorkflowStrategy)

from .model_step import ModelStep


class ModelJob(BaseModel):
    """GitHub Actions workflow job."""

    runs_on: Union[str, List[str]] = Field(..., alias="runs-on")
    steps: List[ModelStep]
    name: Optional[str] = None
    needs: Optional[Union[str, List[str]]] = None
    if_: Optional[str] = Field(None, alias="if")
    env: Optional[Dict[str, str]] = None
    timeout_minutes: Optional[int] = Field(None, alias="timeout-minutes")
    strategy: Optional[WorkflowStrategy] = None
    continue_on_error: Optional[bool] = Field(None, alias="continue-on-error")
    container: Optional[Union[str, Dict[str, Any]]] = None
    services: Optional[WorkflowServices] = None
    outputs: Optional[Dict[str, str]] = None
