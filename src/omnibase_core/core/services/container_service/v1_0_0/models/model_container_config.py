"""
Container configuration model for ONEX container service.

This model defines the configuration options for DI container management
as part of NODEBASE-001 Phase 2 deconstruction.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelContainerConfig(BaseModel):
    """
    Configuration model for container service operations.

    Defines configuration options for ONEXContainer creation, service
    registration, and registry lifecycle management.
    """

    node_id: str = Field(
        ...,
        description="Node identifier for container and service registration",
    )

    enable_service_validation: bool = Field(
        default=True,
        description="Enable validation of service dependencies during registration",
    )

    enable_lifecycle_logging: bool = Field(
        default=True,
        description="Enable detailed logging of container lifecycle events",
    )

    enable_registry_wrapper: bool = Field(
        default=True,
        description="Enable registry wrapper for backward compatibility with Phase 0 pattern",
    )

    container_metadata: dict | None = Field(
        default=None,
        description="Additional metadata to attach to container instance",
    )

    max_service_creation_retries: int = Field(
        default=3,
        description="Maximum number of retries for service creation from dependencies",
        ge=0,
        le=10,
    )
