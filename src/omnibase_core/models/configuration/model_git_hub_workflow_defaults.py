"""GitHub Actions workflow defaults model."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGitHubWorkflowDefaults"]


class ModelGitHubWorkflowDefaults(BaseModel):
    """Defaults for GitHub Actions workflow runs."""

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
        from_attributes=True,
    )

    run: dict[str, str] | None = Field(
        default=None, description="Default shell and working directory for run steps"
    )
