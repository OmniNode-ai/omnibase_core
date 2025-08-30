"""
Cross-domain interface definitions for ONEX model architecture.

This file defines which models can be safely used across domain boundaries
to prevent circular dependencies and maintain clean separation of concerns.

DOMAIN INTERACTION RULES:
========================

1. CORE domain: Can be imported by ALL other domains (foundational)
2. SERVICE domain: Can import from CORE, CONFIGURATION, SECURITY, HEALTH
3. REGISTRY domain: Can import from CORE, CONFIGURATION, SECURITY, HEALTH, VALIDATION
4. HEALTH domain: Can import from CORE only
5. SECURITY domain: Can import from CORE only
6. CONFIGURATION domain: Can import from CORE only
7. VALIDATION domain: Can import from CORE only
8. SCENARIO domain: Can import from CORE, SERVICE, REGISTRY, VALIDATION
9. ENDPOINTS domain: Can import from CORE, CONFIGURATION
10. DETECTION domain: Can import from CORE, SERVICE, CONFIGURATION

CROSS-DOMAIN EXPORTS:
====================
These models are approved for cross-domain usage:
"""

# Security models (for authentication integration)
# Fallback strategy moved to core for circular import resolution

# Configuration models (for service integration)
from .configuration.model_handler_config import *
from .configuration.model_metadata_config import *
# Core models (available to all domains)
from .core.model_base_error import *
from .core.model_base_result import *
from .core.model_context import *
from .core.model_fallback_strategy import *
from .core.model_onex_event import *
from .core.model_onex_message import *
from .core.model_shared_types import *
from .core.model_state_contract import *
# Health models (for monitoring integration)
from .health.model_health_check import *
# Validation models (for testing integration)
from .validation.model_validate_error import *

__all__ = [
    # Cross-domain safe exports
    "BaseError",
    "BaseResult",
    "Context",
    "SharedTypes",
    "OnexEvent",
    "OnexMessage",
    "StateContract",
    "ModelHandlerConfig",
    "MetadataConfig",
    "HealthCheck",
    "ModelFallbackStrategy",
    "FallbackStrategyType",
    "ValidateError",
]

# Domain access documentation
DOMAIN_DEPENDENCIES = {
    "core": [],  # No dependencies (foundational)
    "service": ["core", "configuration", "security", "health"],
    "registry": ["core", "configuration", "security", "health", "validation"],
    "health": ["core"],
    "security": ["core"],
    "configuration": ["core"],
    "validation": ["core"],
    "scenario": ["core", "service", "registry", "validation"],
    "endpoints": ["core", "configuration"],
    "detection": ["core", "service", "configuration"],
}
