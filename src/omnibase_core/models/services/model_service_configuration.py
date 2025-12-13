"""
Service Configuration Models for ONEX Configuration-Driven Registry System.

This module provides the foundational Pydantic models for the configuration-driven
service discovery and registry management system. These models replace hardcoded
service definitions with YAML-driven configuration.

"""

# Import models from extracted files
# NOTE: ModelRegistryConfig import removed to break circular dependency
# Import it directly from omnibase_core.models.registry.model_registry_config instead
from omnibase_core.enums.enum_fallback_strategy_type import EnumFallbackStrategyType
from omnibase_core.models.examples.model_fallback_strategy import ModelFallbackStrategy
from omnibase_core.models.services.model_service_configuration_single import (
    ModelServiceConfiguration,
)
from omnibase_core.models.services.model_service_registry_config import (
    ModelServiceRegistryConfig,
)

# Re-export (excluding ModelRegistryConfig due to circular import)
__all__ = [
    "EnumFallbackStrategyType",
    "ModelFallbackStrategy",
    "ModelServiceConfiguration",
    "ModelServiceRegistryConfig",
]
