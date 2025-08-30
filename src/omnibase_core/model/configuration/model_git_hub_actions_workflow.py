"""
GitHub Actions workflow model.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel

from omnibase_core.model.configuration.model_workflow_configuration import \
    WorkflowPermissions

from .model_job import ModelJob
from .model_workflow_triggers import ModelWorkflowTriggers


class ModelGitHubActionsWorkflow(BaseModel):
    """GitHub Actions workflow model."""

    name: str
    on: ModelWorkflowTriggers
    jobs: Dict[str, ModelJob]
    env: Optional[Dict[str, str]] = None
    defaults: Optional[Dict[str, Any]] = None
    concurrency: Optional[Union[str, Dict[str, Any]]] = None
    permissions: Optional[Union[str, WorkflowPermissions]] = None

    def to_serializable_dict(self) -> Dict[str, Any]:
        """
        Convert to a serializable dictionary with proper field names.
        """

        def serialize_value(val: Any) -> Any:
            if hasattr(val, "to_serializable_dict"):
                return val.to_serializable_dict()
            elif isinstance(val, BaseModel):
                return val.model_dump(by_alias=True, exclude_none=True)
            elif isinstance(val, Enum):
                return val.value
            elif isinstance(val, list):
                return [serialize_value(v) for v in val]
            elif isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            else:
                return val

        return {
            k: serialize_value(getattr(self, k))
            for k in self.model_fields
            if getattr(self, k) is not None
        }

    @classmethod
    def from_serializable_dict(
        cls, data: Dict[str, Any]
    ) -> "ModelGitHubActionsWorkflow":
        """
        Create from a serializable dictionary.
        """
        return cls(**data)
