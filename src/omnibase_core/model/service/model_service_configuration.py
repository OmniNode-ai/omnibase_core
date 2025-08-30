"""
Service Configuration Models for ONEX Configuration-Driven Registry System.

This module provides the foundational Pydantic models for the configuration-driven
service discovery and registry management system. These models replace hardcoded
service definitions with YAML-driven configuration.

Author: OmniNode Team
"""

# Import models from extracted files for backward compatibility
# NOTE: ModelRegistryConfig import removed to break circular dependency
# Import it directly from omnibase_core.model.registry.model_registry_config instead
from omnibase_core.model.core.model_fallback_strategy import (
    FallbackStrategyType, ModelFallbackStrategy)
from omnibase_core.model.service.model_service_configuration_single import \
    ModelServiceConfiguration
from omnibase_core.model.service.model_service_registry_config import \
    ModelServiceRegistryConfig

# Re-export for backward compatibility (excluding ModelRegistryConfig due to circular import)
__all__ = [
    "FallbackStrategyType",
    "ModelFallbackStrategy",
    "ModelServiceConfiguration",
    "ModelServiceRegistryConfig",
]
