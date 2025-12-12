"""
GitHub Actions workflow model.
"""

from enum import Enum
from typing import Self

from pydantic import BaseModel, Field

from .model_job import ModelJob
from .model_workflow_permissions import ModelWorkflowPermissions
from .model_workflow_triggers import ModelWorkflowTriggers


class ModelGitHubWorkflowDefaults(BaseModel):
    """Defaults for GitHub Actions workflow runs."""

    run: dict[str, str] | None = Field(
        default=None, description="Default shell and working directory for run steps"
    )


class ModelGitHubWorkflowConcurrency(BaseModel):
    """Concurrency settings for GitHub Actions workflow."""

    group: str = Field(default=..., description="Concurrency group name")
    cancel_in_progress: bool = Field(
        default=False, description="Cancel in-progress runs"
    )


class ModelGitHubWorkflowData(BaseModel):
    """Serializable workflow data structure."""

    name: str
    on: dict[str, object] | None = None
    jobs: dict[str, dict[str, object]]
    env: dict[str, str] | None = None
    defaults: dict[str, str] | None = None
    concurrency: dict[str, object] | None = None
    permissions: dict[str, str] | None = None


class ModelGitHubActionsWorkflow(BaseModel):
    """GitHub Actions workflow model."""

    name: str
    on: ModelWorkflowTriggers
    jobs: dict[str, ModelJob]
    env: dict[str, str] | None = None
    defaults: ModelGitHubWorkflowDefaults | None = None
    concurrency: ModelGitHubWorkflowConcurrency | None = None
    permissions: ModelWorkflowPermissions | None = None

    def to_serializable_dict(self) -> ModelGitHubWorkflowData:
        """
        Convert to a serializable dictionary with proper field names.
        """

        def serialize_value(val: object) -> object:
            if hasattr(val, "to_serializable_dict"):
                return val.to_serializable_dict()  # type: ignore[union-attr]
            if isinstance(val, BaseModel):
                return val.model_dump(by_alias=True, exclude_none=True)
            if isinstance(val, Enum):
                return val.value
            if isinstance(val, list):
                return [serialize_value(v) for v in val]
            if isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            return val

        data = {
            k: serialize_value(getattr(self, k))
            for k in self.__class__.model_fields
            if getattr(self, k) is not None
        }
        return ModelGitHubWorkflowData(**data)  # type: ignore[arg-type]

    @classmethod
    def from_serializable_dict(
        cls,
        data: ModelGitHubWorkflowData,
    ) -> Self:
        """
        Create from a serializable dictionary.
        """
        return cls(**data.model_dump())
