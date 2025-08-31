"""
Backward compatibility module for tool collection models.

This module maintains compatibility while redirecting to the new enhanced models:
- ModelToolCollection -> model_enhanced_tool_collection.py (enhanced)
- ModelMetadataToolCollection -> model_metadata_tool_collection.py (enhanced)

All functionality is preserved through re-exports with massive enterprise enhancements.
"""

# Re-export enhanced models for backward compatibility
from omnibase_core.model.core.model_enhanced_tool_collection import (
    ModelToolCollection,
    ToolCapabilityLevel,
    ToolCategory,
    ToolCompatibilityMode,
    ToolMetadata,
    ToolPerformanceMetrics,
    ToolRegistrationStatus,
    ToolValidationResult,
)
from omnibase_core.model.core.model_metadata_tool_collection import (
    MetadataToolAnalytics,
    MetadataToolComplexity,
    MetadataToolInfo,
    MetadataToolStatus,
    MetadataToolType,
    MetadataToolUsageMetrics,
    ModelMetadataToolCollection,
)

# Ensure all original functionality is available
__all__ = [
    "LegacyToolCollection",
    "MetadataToolAnalytics",
    "MetadataToolCollection",
    "MetadataToolComplexity",
    "MetadataToolInfo",
    "MetadataToolStatus",
    # Enhanced enums and classes for MetadataToolCollection
    "MetadataToolType",
    "MetadataToolUsageMetrics",
    "ModelMetadataToolCollection",
    # Original models (enhanced)
    "ModelToolCollection",
    "ToolCapabilityLevel",
    "ToolCategory",
    # Legacy aliases (preserved)
    "ToolCollection",
    "ToolCompatibilityMode",
    "ToolMetadata",
    "ToolPerformanceMetrics",
    # Enhanced enums and classes for ToolCollection
    "ToolRegistrationStatus",
    "ToolValidationResult",
]

# Legacy aliases for backward compatibility during migration
ToolCollection = ModelToolCollection
MetadataToolCollection = ModelMetadataToolCollection
LegacyToolCollection = ModelMetadataToolCollection
