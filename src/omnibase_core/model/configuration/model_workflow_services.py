"""
Workflow services model.
"""

from typing import Any

from pydantic import BaseModel, Field

from .model_service_container import ModelServiceContainer


class ModelWorkflowServices(BaseModel):
    """
    Workflow services configuration with typed fields.
    Replaces Dict[str, Any] for services fields.
    """

    services: dict[str, ModelServiceContainer] = Field(
        default_factory=dict,
        description="Service definitions",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # Custom transformation using model_dump() for each service
        return {
            name: service.model_dump(exclude_none=True)
            for name, service in self.services.items()
        }
