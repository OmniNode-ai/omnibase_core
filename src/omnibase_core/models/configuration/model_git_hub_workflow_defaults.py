"""GitHub Actions workflow defaults model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGitHubWorkflowDefaults"]


class ModelGitHubWorkflowDefaults(BaseModel):
    """Defaults for GitHub Actions workflow runs."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
    )

    run: dict[str, str] | None = Field(
        default=None, description="Default shell and working directory for run steps"
    )
