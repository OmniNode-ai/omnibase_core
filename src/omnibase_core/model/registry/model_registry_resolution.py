"""
Registry Resolution Models - Backward Compatibility Module.

This module re-exports the enhanced registry resolution models that have been
extracted to separate files for better maintainability and standards compliance.

For new code, import directly from the specific model files:
- from omnibase_core.model.registry.model_registry_resolution_context import ModelRegistryResolutionContext
- from omnibase_core.model.registry.model_registry_resolution_result import ModelRegistryResolutionResult
"""

# Re-export enhanced models for backward compatibility
from .model_registry_resolution_context import ModelRegistryResolutionContext
from .model_registry_resolution_result import ModelRegistryResolutionResult

# Maintain backward compatibility with any existing imports
__all__ = ["ModelRegistryResolutionContext", "ModelRegistryResolutionResult"]
