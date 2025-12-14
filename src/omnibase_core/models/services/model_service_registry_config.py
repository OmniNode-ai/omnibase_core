"""
Service Registry Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceRegistryConfig for complete service registry configuration.
Extracted from model_service_configuration.py for modular architecture compliance.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.registry.model_registry_mode_config import (
        ModelRegistryModeConfig,
    )
    from omnibase_core.models.services.model_service_configuration_single import (
        ModelServiceConfiguration,
    )


class ModelServiceRegistryConfig(BaseModel):
    """Complete service registry configuration."""

    services: dict[str, ModelServiceConfiguration] = Field(
        default_factory=dict,
        description="Service configurations keyed by service name",
    )
    registry_modes: dict[str, ModelRegistryModeConfig] = Field(
        default_factory=dict,
        description="Registry mode configurations",
    )
    default_mode: str = Field(
        default="development",
        description="Default registry mode if not specified",
    )
    configuration_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Configuration schema version",
    )

    @field_validator("services")
    @classmethod
    def validate_services_not_empty(cls, v: Any, info: Any) -> Any:
        if not v:
            msg = "At least one service must be configured"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("registry_modes")
    @classmethod
    def validate_default_mode_exists(cls, v: Any, info: Any) -> Any:
        if hasattr(info, "data") and info.data:
            default_mode = info.data.get("default_mode")
            if default_mode and default_mode not in v:
                msg = f"Default mode '{default_mode}' not found in registry_modes"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
        return v

    def get_service_names(self) -> list[str]:
        """Get list[Any]of all configured service names."""
        return list(self.services.keys())

    def get_mode_names(self) -> list[str]:
        """Get list[Any]of all configured registry mode names."""
        return list(self.registry_modes.keys())

    def get_service(self, service_name: str) -> ModelServiceConfiguration | None:
        """Get a specific service configuration."""
        return self.services.get(service_name)

    def get_mode(self, mode_name: str) -> ModelRegistryModeConfig | None:
        """Get a specific registry mode configuration."""
        return self.registry_modes.get(mode_name)

    def has_service(self, service_name: str) -> bool:
        """Check if a service is configured."""
        return service_name in self.services

    def has_mode(self, mode_name: str) -> bool:
        """Check if a registry mode is configured."""
        return mode_name in self.registry_modes

    def get_critical_services(self) -> list[str]:
        """Get list[Any]of critical service names."""
        return [
            name
            for name, config in self.services.items()
            if config.is_critical_service()
        ]

    def get_high_priority_services(self) -> list[str]:
        """Get list[Any]of high priority service names."""
        return [
            name for name, config in self.services.items() if config.is_high_priority()
        ]

    def get_services_by_type(self, service_type: str) -> list[str]:
        """Get service names filtered by service type."""
        return [
            name
            for name, config in self.services.items()
            if config.get_service_type_name() == service_type
        ]

    def get_required_services_for_mode(self, mode_name: str) -> list[str]:
        """Get required services for a specific mode."""
        mode_config = self.get_mode(mode_name)
        if not mode_config:
            return []
        required_services: list[str] = mode_config.required_services
        return required_services

    def add_service(self, name: str, config: ModelServiceConfiguration) -> None:
        """Add a new service configuration."""
        self.services[name] = config

    def add_mode(self, name: str, config: ModelRegistryModeConfig) -> None:
        """Add a new registry mode configuration."""
        self.registry_modes[name] = config

    def remove_service(self, name: str) -> bool:
        """Remove a service configuration. Returns True if removed."""
        if name in self.services:
            del self.services[name]
            return True
        return False

    def remove_mode(self, name: str) -> bool:
        """Remove a registry mode configuration. Returns True if removed."""
        if name in self.registry_modes:
            del self.registry_modes[name]
            return True
        return False
