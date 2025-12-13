"""GitHub Actions workflow concurrency model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGitHubWorkflowConcurrency"]


class ModelGitHubWorkflowConcurrency(BaseModel):
    """Concurrency settings for GitHub Actions workflow."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
    )

    group: str = Field(default=..., description="Concurrency group name")
    cancel_in_progress: bool = Field(
        default=False, description="Cancel in-progress runs"
    )
