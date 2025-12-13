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
    ToolCollection,
    ToolMetadata,
    ToolPerformanceMetrics,
    ToolValidationResult,
)
from omnibase_core.models.core.model_metadata_tool_collection import (
    EnumMetadataToolComplexity,
    EnumMetadataToolStatus,
    EnumMetadataToolType,
    MetadataToolAnalytics,
    MetadataToolCollection,
    MetadataToolInfo,
    MetadataToolUsageMetrics,
    ModelMetadataToolAnalytics,
    ModelMetadataToolCollection,
    ModelMetadataToolInfo,
    ModelMetadataToolUsageMetrics,
)

# Re-export all models and compatibility aliases
__all__ = [
    # Enhanced tool collection models
    "EnumToolCapabilityLevel",
    "EnumToolCategory",
    "EnumToolCompatibilityMode",
    "EnumToolRegistrationStatus",
    "ModelToolCollection",
    "ToolCollection",
    "ToolMetadata",
    "ToolPerformanceMetrics",
    "ToolValidationResult",
    # Metadata tool collection models
    "EnumMetadataToolComplexity",
    "EnumMetadataToolStatus",
    "EnumMetadataToolType",
    "MetadataToolAnalytics",
    "MetadataToolCollection",
    "MetadataToolInfo",
    "MetadataToolUsageMetrics",
    "ModelMetadataToolAnalytics",
    "ModelMetadataToolCollection",
    "ModelMetadataToolInfo",
    "ModelMetadataToolUsageMetrics",
]
