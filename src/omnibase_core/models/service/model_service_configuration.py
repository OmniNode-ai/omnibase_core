"""
Service Configuration Models for ONEX Configuration-Driven Registry System.

This module provides the foundational Pydantic models for the configuration-driven
service discovery and registry management system. These models replace hardcoded
service definitions with YAML-driven configuration.

Author: OmniNode Team
"""

# Import models from extracted files
# NOTE: ModelRegistryConfig import removed to break circular dependency
# Import it directly from omnibase_core.models.registry.model_registry_config instead
from omnibase_core.models.config.model_fallback_strategy import (
    EnumFallbackStrategyType,
    ModelFallbackStrategy,
)
from omnibase_core.models.service.model_service_configuration_single import (
    ModelServiceConfiguration,
)
from omnibase_core.models.service.model_service_registry_config import (
    ModelServiceRegistryConfig,
)

# Re-export (excluding ModelRegistryConfig due to circular import)
__all__ = [
    "EnumFallbackStrategyType",
    "ModelFallbackStrategy",
    "ModelServiceConfiguration",
    "ModelServiceRegistryConfig",
]
