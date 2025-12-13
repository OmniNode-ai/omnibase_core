"""GitHub Actions workflow data model."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelGitHubWorkflowData"]


class ModelGitHubWorkflowData(BaseModel):
    """Serializable workflow data structure."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
        from_attributes=True,
    )

    name: str
    on: str | list[str] | dict[str, object] | None = None
    jobs: dict[str, dict[str, object]]
    env: dict[str, str] | None = None
    defaults: dict[str, object] | None = None
    concurrency: str | dict[str, object] | None = None
    permissions: str | dict[str, str] | None = None
