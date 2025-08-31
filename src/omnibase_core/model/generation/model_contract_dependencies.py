"""
Contract dependency models for dependency injection integration.

Extends the contract system to specify dependencies that should be injected
into generated tools, enabling contract-driven dependency injection.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class DependencyType(str, Enum):
    """Types of dependencies that can be specified in contracts."""

    PROTOCOL = "protocol"
    CONSUL_SERVICE = "consul_service"
    CONFIGURATION = "configuration"
    STATIC_SERVICE = "static_service"


class ModelProtocolDependency(BaseModel):
    """Protocol-based dependency specification."""

    name: str = Field(..., description="Dependency identifier")
    interface: str = Field(..., description="Python protocol interface path")
    required: bool = Field(True, description="Whether dependency is required")
    description: str | None = Field(None, description="Dependency description")
    fallback: str | None = Field(
        None,
        description="Fallback implementation identifier",
    )

    @field_validator("interface")
    @classmethod
    def validate_interface(cls, v: str) -> str:
        """Validate protocol interface path format."""
        if not v or not isinstance(v, str):
            msg = "interface must be a non-empty string"
            raise ValueError(msg)

        # Should be importable Python path
        parts = v.split(".")
        if len(parts) < 2:
            msg = "interface must be a valid Python import path"
            raise ValueError(msg)

        return v


class ModelConsulServiceDependency(BaseModel):
    """Consul service discovery dependency specification."""

    service_name: str = Field(..., description="Consul service name")
    protocol: str = Field(..., description="Protocol interface identifier")
    interface: str = Field(..., description="Python protocol interface path")
    required: bool = Field(True, description="Whether service is required")
    description: str | None = Field(None, description="Service description")
    fallback: str | None = Field(None, description="Fallback implementation")
    health_check: str | None = Field(None, description="Health check endpoint path")
    timeout_seconds: int = Field(10, description="Service discovery timeout")

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate Consul service name format."""
        if not v or not isinstance(v, str):
            msg = "service_name must be a non-empty string"
            raise ValueError(msg)

        # Consul service names should be lowercase with hyphens
        if not v.replace("-", "").replace("_", "").isalnum():
            msg = "service_name must contain only alphanumeric, hyphens, underscores"
            raise ValueError(
                msg,
            )

        return v


class ModelConfigurationDependency(BaseModel):
    """Configuration section dependency specification."""

    section: str = Field(..., description="Configuration section path")
    required: bool = Field(True, description="Whether configuration is required")
    description: str | None = Field(None, description="Configuration description")
    default_value: Any | None = Field(None, description="Default value if missing")
    validation_schema: dict[str, Any] | None = Field(
        None,
        description="JSON schema for configuration validation",
    )

    @field_validator("section")
    @classmethod
    def validate_section(cls, v: str) -> str:
        """Validate configuration section path."""
        if not v or not isinstance(v, str):
            msg = "section must be a non-empty string"
            raise ValueError(msg)

        # Should be dot-separated path like "logging.engine"
        if not all(part.replace("_", "").isalnum() for part in v.split(".")):
            msg = "section must be dot-separated alphanumeric path"
            raise ValueError(msg)

        return v


class ModelStaticServiceDependency(BaseModel):
    """Static service dependency specification."""

    name: str = Field(..., description="Service identifier")
    protocol: str = Field(..., description="Protocol interface identifier")
    interface: str = Field(..., description="Python protocol interface path")
    required: bool = Field(True, description="Whether service is required")
    description: str | None = Field(None, description="Service description")
    factory: str | None = Field(
        None,
        description="Factory function for creating service",
    )


class ModelContractDependencies(BaseModel):
    """Complete dependency specification for a contract."""

    protocols: list[ModelProtocolDependency] = Field(
        default_factory=list,
        description="Protocol-based dependencies",
    )
    consul_services: list[ModelConsulServiceDependency] = Field(
        default_factory=list,
        description="Consul service discovery dependencies",
    )
    configuration: list[ModelConfigurationDependency] = Field(
        default_factory=list,
        description="Configuration section dependencies",
    )
    static_services: list[ModelStaticServiceDependency] = Field(
        default_factory=list,
        description="Static service dependencies",
    )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelContractDependencies"]:
        """Create from contract dict data."""
        if data is None:
            return None

        # Parse protocol dependencies
        protocols = []
        if "protocols" in data:
            for proto_data in data["protocols"]:
                protocols.append(ModelProtocolDependency(**proto_data))

        # Parse consul service dependencies
        consul_services = []
        if "consul_services" in data:
            for service_data in data["consul_services"]:
                consul_services.append(ModelConsulServiceDependency(**service_data))

        # Parse configuration dependencies
        configuration = []
        if "configuration" in data:
            for config_data in data["configuration"]:
                configuration.append(ModelConfigurationDependency(**config_data))

        # Parse static service dependencies
        static_services = []
        if "static_services" in data:
            for service_data in data["static_services"]:
                static_services.append(ModelStaticServiceDependency(**service_data))

        return cls(
            protocols=protocols,
            consul_services=consul_services,
            configuration=configuration,
            static_services=static_services,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {}

        if self.protocols:
            result["protocols"] = [
                proto.model_dump(exclude_none=True) for proto in self.protocols
            ]

        if self.consul_services:
            result["consul_services"] = [
                service.model_dump(exclude_none=True)
                for service in self.consul_services
            ]

        if self.configuration:
            result["configuration"] = [
                config.model_dump(exclude_none=True) for config in self.configuration
            ]

        if self.static_services:
            result["static_services"] = [
                service.model_dump(exclude_none=True)
                for service in self.static_services
            ]

        return result

    def get_all_protocols(self) -> list[str]:
        """Get all protocol interfaces referenced in dependencies."""
        protocols = set()

        # From protocol dependencies
        for proto in self.protocols:
            protocols.add(proto.interface)

        # From consul service dependencies
        for service in self.consul_services:
            protocols.add(service.interface)

        # From static service dependencies
        for service in self.static_services:
            protocols.add(service.interface)

        return sorted(protocols)

    def get_required_protocols(self) -> list[str]:
        """Get all required protocol interfaces."""
        protocols = set()

        # Required protocol dependencies
        for proto in self.protocols:
            if proto.required:
                protocols.add(proto.interface)

        # Required consul service dependencies
        for service in self.consul_services:
            if service.required:
                protocols.add(service.interface)

        # Required static service dependencies
        for service in self.static_services:
            if service.required:
                protocols.add(service.interface)

        return sorted(protocols)

    def get_consul_services(self) -> list[str]:
        """Get all Consul service names referenced."""
        return [service.service_name for service in self.consul_services]

    def get_configuration_sections(self) -> list[str]:
        """Get all configuration sections referenced."""
        return [config.section for config in self.configuration]

    def has_dependencies(self) -> bool:
        """Check if any dependencies are specified."""
        return bool(
            self.protocols
            or self.consul_services
            or self.configuration
            or self.static_services,
        )

    def validate_dependency_graph(self) -> list[str]:
        """Validate dependency graph for circular references and missing protocols."""
        errors = []

        # Check for duplicate dependency names
        names = set()
        for proto in self.protocols:
            if proto.name in names:
                errors.append(f"Duplicate protocol dependency: {proto.name}")
            names.add(proto.name)

        for service in self.consul_services:
            service_name = f"consul:{service.service_name}"
            if service_name in names:
                errors.append(
                    f"Duplicate consul service dependency: {service.service_name}",
                )
            names.add(service_name)

        # TODO: Add more sophisticated dependency graph validation
        # - Circular reference detection
        # - Fallback chain validation
        # - Protocol interface availability checking

        return errors
