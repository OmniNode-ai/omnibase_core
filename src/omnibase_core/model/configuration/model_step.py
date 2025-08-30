"""
Step model.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from .model_step_with import ModelStepWith


class ModelStep(BaseModel):
    """GitHub Actions workflow step."""

    name: Optional[str] = None
    uses: Optional[str] = None
    run: Optional[str] = None
    with_: Optional[ModelStepWith] = Field(None, alias="with")
    env: Optional[Dict[str, str]] = None
    if_: Optional[str] = Field(None, alias="if")
    continue_on_error: Optional[bool] = Field(None, alias="continue-on-error")
    timeout_minutes: Optional[int] = Field(None, alias="timeout-minutes")
    working_directory: Optional[str] = Field(None, alias="working-directory")
