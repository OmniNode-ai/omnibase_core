"""
Container Instance Model

Pydantic model for ONEX container instances used in service resolution.
"""

from pydantic import BaseModel, Field


class ModelServiceRegistration(BaseModel):
    """Service registration entry in container."""

    service_name: str = Field(description="Unique service identifier")
    implementation_class: str = Field(description="Full class path for implementation")
    initialization_params: dict[str, str] = Field(
        default_factory=dict,
        description="Initialization parameters",
    )
    is_singleton: bool = Field(default=True, description="Whether service is singleton")


class ModelProtocolRegistration(BaseModel):
    """Protocol registration entry in container."""

    protocol_name: str = Field(description="Protocol identifier")
    implementation_class: str = Field(description="Full class path for implementation")
    binding_strategy: str = Field(
        default="duck_typing",
        description="How protocol is bound to implementation",
    )


class ModelContainerInstance(BaseModel):
    """Container instance model for service resolution."""

    container_id: str = Field(description="Unique identifier for container instance")
    service_registrations: list[ModelServiceRegistration] = Field(
        default_factory=list,
        description="Registered services",
    )
    protocol_registrations: list[ModelProtocolRegistration] = Field(
        default_factory=list,
        description="Registered protocol implementations",
    )

    class Config:
        frozen = False
