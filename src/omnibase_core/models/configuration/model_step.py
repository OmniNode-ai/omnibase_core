"""
Step model.
"""

from pydantic import BaseModel, Field

from .model_step_with import ModelStepWith


class ModelStep(BaseModel):
    """GitHub Actions workflow step."""

    name: str | None = None
    uses: str | None = None
    run: str | None = None
    with_: ModelStepWith | None = Field(default=None, alias="with")
    env: dict[str, str] | None = None
    if_: str | None = Field(default=None, alias="if")
    continue_on_error: bool | None = Field(default=None, alias="continue-on-error")
    timeout_minutes: int | None = Field(default=None, alias="timeout-minutes")
    working_directory: str | None = Field(default=None, alias="working-directory")
