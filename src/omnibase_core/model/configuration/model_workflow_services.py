"""
Workflow services model.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field

from .model_service_container import ModelServiceContainer


class ModelWorkflowServices(BaseModel):
    """
    Workflow services configuration with typed fields.
    Replaces Dict[str, Any] for services fields.
    """

    services: Dict[str, ModelServiceContainer] = Field(
        default_factory=dict, description="Service definitions"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            name: service.dict(exclude_none=True)
            for name, service in self.services.items()
        }
