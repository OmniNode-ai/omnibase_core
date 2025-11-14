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
    "ModelMetadataToolCollection",
]

# Legacy aliases for current standards during migration
ToolCollection = ModelToolCollection
MetadataToolCollection = ModelMetadataToolCollection
LegacyToolCollection = ModelMetadataToolCollection

# Enum aliases without Model/Enum prefix for convenience
ToolCapabilityLevel = EnumToolCapabilityLevel
ToolCategory = EnumToolCategory
ToolCompatibilityMode = EnumToolCompatibilityMode
ToolRegistrationStatus = EnumToolRegistrationStatus
MetadataToolComplexity = EnumMetadataToolComplexity
MetadataToolStatus = EnumMetadataToolStatus
MetadataToolType = EnumMetadataToolType
