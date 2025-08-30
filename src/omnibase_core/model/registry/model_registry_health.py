"""
Registry Health Models - Backward Compatibility Module.

This module re-exports the enhanced registry health models that have been
extracted to separate files for better maintainability and standards compliance.

For new code, import directly from the specific model files:
- from omnibase_core.model.health.model_tool_health import ModelToolHealth
- from omnibase_core.model.service.model_service_health import ModelServiceHealth
- from omnibase_core.model.registry.model_registry_health_report import ModelRegistryHealthReport
"""

# Re-export enhanced models for backward compatibility
from omnibase_core.model.health.model_tool_health import ModelToolHealth
from omnibase_core.model.service.model_service_health import ModelServiceHealth

from .model_registry_health_report import ModelRegistryHealthReport

# Maintain backward compatibility with any existing imports
__all__ = ["ModelToolHealth", "ModelServiceHealth", "ModelRegistryHealthReport"]
