"""
Modern standards module for tool collection models.

This module maintains compatibility while redirecting to the new enhanced models:
- ModelToolCollection -> model_enhanced_tool_collection.py (enhanced)
- ModelMetadataToolCollection -> model_metadata_tool_collection.py (enhanced)

All functionality is preserved through re-exports with massive enterprise enhancements.
"""

# Re-export enhanced models for current standards
from omnibase_core.models.core.model_enhanced_tool_collection import (
    EnumToolCapabilityLevel,
    EnumToolCategory,
    EnumToolCompatibilityMode,
    EnumToolRegistrationStatus,
    ModelToolCollection,
    ToolMetadata,
    ToolPerformanceMetrics,
    ToolValidationResult,
)
from omnibase_core.models.core.model_metadata_tool_collection import (
    EnumMetadataToolComplexity,
    EnumMetadataToolStatus,
    EnumMetadataToolType,
    MetadataToolAnalytics,
    MetadataToolInfo,
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

# Legacy aliases for current standards during migration
ToolCollection = ModelToolCollection
MetadataToolCollection = ModelMetadataToolCollection
LegacyToolCollection = ModelMetadataToolCollection
