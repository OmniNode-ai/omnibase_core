"""
Modern standards module for node collection models.

This module maintains compatibility while redirecting to the new enhanced models:
- ModelNodeCollection -> model_enhanced_node_collection.py (enhanced)
- ModelMetadataNodeCollection -> model_metadata_node_collection.py (enhanced)

All functionality is preserved through re-exports with massive enterprise enhancements.
"""

# Re-export enhanced models for current standards
from omnibase_core.models.core.model_enhanced_node_collection import (
    ModelNodeCollection,
    NodeCapabilityLevel,
    NodeCategory,
    NodeCompatibilityMode,
    NodeMetadata,
    NodePerformanceMetrics,
    NodeRegistrationStatus,
    NodeValidationResult,
)
from .model_metadata_node_collection import (
    ModelMetadataNodeCollection,
)
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_info import (
    ModelMetadataNodeComplexity,
    ModelMetadataNodeInfo,
    ModelMetadataNodeStatus,
    ModelMetadataNodeType,
)
from .model_metadata_node_usage_metrics import ModelMetadataNodeUsageMetrics

# Create aliases for backward compatibility
MetadataNodeAnalytics = ModelMetadataNodeAnalytics
MetadataNodeComplexity = ModelMetadataNodeComplexity
MetadataNodeInfo = ModelMetadataNodeInfo
MetadataNodeStatus = ModelMetadataNodeStatus
MetadataNodeType = ModelMetadataNodeType
MetadataNodeUsageMetrics = ModelMetadataNodeUsageMetrics

# Ensure all original functionality is available
__all__ = [
    "LegacyNodeCollection",
    "MetadataNodeAnalytics",
    "MetadataNodeCollection",
    "MetadataNodeComplexity",
    "MetadataNodeInfo",
    "MetadataNodeStatus",
    # Enhanced enums and classes for MetadataNodeCollection
    "MetadataNodeType",
    "MetadataNodeUsageMetrics",
    "ModelMetadataNodeCollection",
    # Original models (enhanced)
    "ModelNodeCollection",
    "NodeCapabilityLevel",
    "NodeCategory",
    # Legacy aliases (preserved)
    "NodeCollection",
    "NodeCompatibilityMode",
    "NodeMetadata",
    "NodePerformanceMetrics",
    # Enhanced enums and classes for NodeCollection
    "NodeRegistrationStatus",
    "NodeValidationResult",
]

# Legacy aliases for current standards during migration
NodeCollection = ModelNodeCollection
MetadataNodeCollection = ModelMetadataNodeCollection
LegacyNodeCollection = ModelMetadataNodeCollection
