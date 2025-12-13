"""GitHub Actions workflow data model."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelGitHubWorkflowData"]


class ModelGitHubWorkflowData(BaseModel):
    """Serializable workflow data structure."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
    )

    name: str
    on: dict[str, object] | None = None
    jobs: dict[str, dict[str, object]]
    env: dict[str, str] | None = None
    defaults: dict[str, str] | None = None
    concurrency: dict[str, object] | None = None
    permissions: dict[str, str] | None = None
