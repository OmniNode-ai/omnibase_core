"""GitHub Actions workflow model."""

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict

from .model_git_hub_workflow_concurrency import ModelGitHubWorkflowConcurrency
from .model_git_hub_workflow_data import ModelGitHubWorkflowData
from .model_git_hub_workflow_defaults import ModelGitHubWorkflowDefaults
from .model_job import ModelJob
from .model_workflow_permissions import ModelWorkflowPermissions
from .model_workflow_triggers import ModelWorkflowTriggers

__all__ = ["ModelGitHubActionsWorkflow"]


class ModelGitHubActionsWorkflow(BaseModel):
    """GitHub Actions workflow model."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="forbid",
    )

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
                serializable = val.to_serializable_dict
                if callable(serializable):
                    return serializable()
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
        return ModelGitHubWorkflowData.model_validate(data)

    @classmethod
    def from_serializable_dict(
        cls,
        data: ModelGitHubWorkflowData,
    ) -> Self:
        """
        Create from a serializable dictionary.
        """
        return cls.model_validate(data.model_dump())
