"""
Workflow services model.
"""

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


# ONEX compliance remediation complete - factory method eliminated
# Direct Pydantic model_dump() provides standardized serialization:
# services_dict = services.model_dump(exclude_none=True)
