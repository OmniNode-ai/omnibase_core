"""GitHub Actions workflow concurrency model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGitHubWorkflowConcurrency"]


class ModelGitHubWorkflowConcurrency(BaseModel):
    """Concurrency settings for GitHub Actions workflow."""

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
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
