from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
GitHub Actions workflow model.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel

from omnibase_core.models.configuration.model_workflow_configuration import (
    WorkflowPermissions,
)

from .model_job import ModelJob
from .model_workflow_triggers import ModelWorkflowTriggers


class ModelGitHubActionsWorkflow(BaseModel):
    """GitHub Actions workflow model."""

    name: str
    on: ModelWorkflowTriggers
    jobs: dict[str, ModelJob]
    env: dict[str, str] | None = None
    defaults: dict[str, Any] | None = None
    concurrency: Any = None
    permissions: Any = None

    def to_serializable_dict(self) -> dict[str, Any]:
        """
        Convert to a serializable dictionary with proper field names.
        """

        def serialize_value(val: Any) -> Any:
            if hasattr(val, "to_serializable_dict"):
                return val.to_serializable_dict()
            if isinstance(val, BaseModel):
                return val.model_dump(by_alias=True, exclude_none=True)
            if isinstance(val, Enum):
                return val.value
            if isinstance(val, list):
                return [serialize_value(v) for v in val]
            if isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            return val

        return {
            k: serialize_value(getattr(self, k))
            for k in self.__class__.model_fields
            if getattr(self, k) is not None
        }

    @classmethod
    def from_serializable_dict(
        cls,
        data: dict[str, Any],
    ) -> "ModelGitHubActionsWorkflow":
        """
        Create from a serializable dictionary.
        """
        return cls(**data)
