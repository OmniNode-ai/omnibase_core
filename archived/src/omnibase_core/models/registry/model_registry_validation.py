"""
Registry Validation Models - Compatibility Module.

This module re-exports the enhanced registry validation models that have been
extracted to separate files for better maintainability and standards compliance.

For new code, import directly from the specific model files:
- from omnibase_core.models.core.model_missing_tool import ModelMissingTool
- from omnibase_core.models.registry.model_registry_validation_result import ModelRegistryValidationResult
"""

# Re-export enhanced models
from omnibase_core.models.core.model_missing_tool import ModelMissingTool

from .model_registry_validation_result import ModelRegistryValidationResult

# Maintain imports
__all__ = ["ModelMissingTool", "ModelRegistryValidationResult"]
