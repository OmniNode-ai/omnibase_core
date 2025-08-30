"""
Registry Validation Models - Backward Compatibility Module.

This module re-exports the enhanced registry validation models that have been
extracted to separate files for better maintainability and standards compliance.

For new code, import directly from the specific model files:
- from omnibase_core.model.core.model_missing_tool import ModelMissingTool
- from omnibase_core.model.registry.model_registry_validation_result import ModelRegistryValidationResult
"""

# Re-export enhanced models for backward compatibility
from omnibase_core.model.core.model_missing_tool import ModelMissingTool

from .model_registry_validation_result import ModelRegistryValidationResult

# Maintain backward compatibility with any existing imports
__all__ = ["ModelMissingTool", "ModelRegistryValidationResult"]
