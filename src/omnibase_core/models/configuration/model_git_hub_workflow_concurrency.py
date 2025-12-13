"""GitHub Actions workflow concurrency model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGitHubWorkflowConcurrency"]


class ModelGitHubWorkflowConcurrency(BaseModel):
    """Concurrency settings for GitHub Actions workflow."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )

    group: str = Field(default=..., description="Concurrency group name")
    cancel_in_progress: bool = Field(
        default=False,
        description="Cancel in-progress runs",
        serialization_alias="cancel-in-progress",
        validation_alias="cancel-in-progress",
    )
