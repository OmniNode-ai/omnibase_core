"""
Container service result model for ONEX container operations.

This model encapsulates the results of container service operations
as part of NODEBASE-001 Phase 2 deconstruction.

Author: ONEX Framework Team
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelContainerResult(BaseModel):
    """
    Result model for container service operations.

    Encapsulates the results of container creation, service registration,
    and registry lifecycle operations with comprehensive metadata.
    """

    container: Any = Field(..., description="Created ONEXContainer instance")

    registry: Any = Field(..., description="Registry wrapper for container access")

    registered_services: list[str] = Field(
        default_factory=list,
        description="List of service names successfully registered in container",
    )

    failed_services: list[str] = Field(
        default_factory=list,
        description="List of service names that failed registration",
    )

    service_metadata: dict[str, dict] = Field(
        default_factory=dict,
        description="Metadata about each registered service including creation details",
    )

    validation_results: dict[str, bool] = Field(
        default_factory=dict,
        description="Validation results for each service dependency",
    )

    container_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about container creation and configuration",
    )

    lifecycle_state: str = Field(
        default="initialized",
        description="Current lifecycle state of the container",
    )

    node_reference_attached: bool = Field(
        default=False,
        description="Whether ModelNodeBase reference has been attached to registry",
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
