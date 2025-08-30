"""
Consul service registration configuration models.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# Import and re-export for convenience


class ModelConsulHealthCheck(BaseModel):
    """Configuration for Consul health checks."""

    http: Optional[str] = Field(None, description="HTTP endpoint for health checks")
    tcp: Optional[str] = Field(None, description="TCP endpoint for health checks")
    interval: str = Field("10s", description="Health check interval")
    timeout: str = Field("3s", description="Health check timeout")
    deregister_critical_service_after: str = Field(
        "30s", description="Time to wait before deregistering critical service"
    )


class ModelServiceRegistrationConfig(BaseModel):
    """Configuration for registering a service with Consul."""

    service_name: str = Field(..., description="Name of the service to register")
    service_id: str = Field(
        ..., description="Unique identifier for this service instance"
    )
    service_port: int = Field(..., description="Port on which the service is listening")
    service_address: Optional[str] = Field(
        None, description="Address of the service (defaults to local IP)"
    )
    health_check: Optional[ModelConsulHealthCheck] = Field(
        None, description="Health check configuration"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for service categorization and discovery",
    )
    meta: Dict[str, str] = Field(
        default_factory=dict, description="Metadata key-value pairs for the service"
    )


class ModelServiceRegistrationResult(BaseModel):
    """Result of service registration operation."""

    success: bool = Field(..., description="Whether the registration was successful")
    service_id: str = Field(..., description="The service ID that was registered")
    consul_agent_url: str = Field(
        ..., description="URL of the Consul agent used for registration"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if registration failed"
    )
    registration_timestamp: str = Field(
        ..., description="ISO timestamp when registration occurred"
    )
