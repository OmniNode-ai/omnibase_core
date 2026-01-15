"""
Metadata Node Info Model.

Enhanced node information specifically for metadata collections
with usage metrics and performance tracking.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.enums.enum_validation import EnumValidationLevel
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.metadata.model_metadata_usage_metrics import (
    ModelMetadataUsageMetrics,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_metadata_value import ModelMetadataValue
from .model_node_info_summary import ModelNodeInfoSummary
from .model_structured_description import ModelStructuredDescription
from .model_structured_display_name import ModelStructuredDisplayName
from .model_structured_tags import ModelStructuredTags

# Type aliases for convenience
ModelMetadataNodeType = EnumMetadataNodeType
ModelMetadataNodeStatus = EnumMetadataNodeStatus
ModelMetadataNodeComplexity = EnumConceptualComplexity


class ModelMetadataNodeInfo(BaseModel):
    """
    Enhanced node information for metadata collections.

    Provides detailed metadata, usage tracking, and performance
    metrics for nodes in metadata collections.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identification
    node_id: UUID = Field(default=..., description="UUID for node identifier")

    # Structured naming and description (reduces string fields)
    display_name: ModelStructuredDisplayName = Field(
        default_factory=lambda: ModelStructuredDisplayName.for_metadata_node("default"),
        description="Structured display name with consistent naming patterns",
    )

    description: ModelStructuredDescription = Field(
        default_factory=lambda: ModelStructuredDescription.for_metadata_node("default"),
        description="Structured description with standardized templates",
    )
    node_type: EnumMetadataNodeType = Field(
        default=EnumMetadataNodeType.FUNCTION,
        description="Node type",
    )

    # Status and lifecycle
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: EnumConceptualComplexity = Field(
        default=EnumConceptualComplexity.BASIC,
        description="Node conceptual complexity level",
    )
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Node version",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Categorization (structured)
    tags: ModelStructuredTags = Field(
        default_factory=lambda: ModelStructuredTags.for_metadata_node(),
        description="Structured tags with standard and custom classifications",
    )

    # Categories now handled through tags.primary_category and tags.secondary_categories

    # Documentation and examples
    has_documentation: bool = Field(
        default=False,
        description="Whether node has documentation",
    )
    has_examples: bool = Field(
        default=False,
        description="Whether node has examples",
    )
    documentation_quality: EnumValidationLevel = Field(
        default=EnumValidationLevel.BASIC,
        description="Documentation quality level",
    )

    # Dependencies and relationships
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    related_nodes: list[UUID] = Field(
        default_factory=list,
        description="Related nodes",
    )

    # Usage and performance metrics
    usage_metrics: ModelMetadataUsageMetrics = Field(
        default_factory=lambda: ModelMetadataUsageMetrics(),
        description="Usage and performance metrics",
    )

    # Custom metadata for extensibility
    custom_metadata: dict[str, ModelValue] = Field(
        default_factory=dict,
        description="Custom metadata fields with strongly-typed values",
    )

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == EnumMetadataNodeStatus.ACTIVE

    def is_stable(self) -> bool:
        """Check if node is stable."""
        return self.status == EnumMetadataNodeStatus.STABLE

    def is_experimental(self) -> bool:
        """Check if node is experimental."""
        return self.status == EnumMetadataNodeStatus.EXPERIMENTAL

    def is_simple(self) -> bool:
        """Check if node is simple complexity."""
        return self.complexity == EnumConceptualComplexity.TRIVIAL

    def is_complex(self) -> bool:
        """Check if node is complex."""
        return self.complexity in [
            EnumConceptualComplexity.ADVANCED,
            EnumConceptualComplexity.EXPERT,
        ]

    def has_good_documentation(self) -> bool:
        """Check if node has good documentation."""
        return self.has_documentation and self.documentation_quality in [
            EnumValidationLevel.STANDARD,
            EnumValidationLevel.COMPREHENSIVE,
        ]

    def get_success_rate(self) -> float:
        """Get node success rate."""
        return self.usage_metrics.get_success_rate()

    def get_complexity_score(self) -> int:
        """Get numeric complexity score."""
        complexity_scores = {
            EnumConceptualComplexity.TRIVIAL: 1,
            EnumConceptualComplexity.BASIC: 2,
            EnumConceptualComplexity.INTERMEDIATE: 3,
            EnumConceptualComplexity.ADVANCED: 4,
            EnumConceptualComplexity.EXPERT: 5,
        }
        return complexity_scores.get(self.complexity, 1)

    def add_tag(self, tag: str) -> bool:
        """Add a tag (standard or custom)."""
        # Try as standard tag first
        standard_tag = EnumStandardTag.from_string(tag)
        if standard_tag:
            return self.tags.add_standard_tag(standard_tag)
        return self.tags.add_custom_tag(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag."""
        standard_tag = EnumStandardTag.from_string(tag)
        if standard_tag:
            return self.tags.remove_standard_tag(standard_tag)
        return self.tags.remove_custom_tag(tag)

    def add_category(self, category: str) -> bool:
        """Add a category (as secondary category)."""
        category_enum = EnumStandardCategory.from_string(category)
        if category_enum and category_enum not in self.tags.secondary_categories:
            self.tags.secondary_categories.append(category_enum)
            return True
        return False

    def add_dependency(self, dependency: UUID) -> None:
        """Add a dependency if not already present."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def add_related_node(self, node_id: UUID) -> None:
        """Add a related node if not already present."""
        if node_id not in self.related_nodes:
            self.related_nodes.append(node_id)

    def mark_active(self) -> None:
        """Mark node as active."""
        self.status = EnumMetadataNodeStatus.ACTIVE
        self.update_timestamp()

    def mark_stable(self) -> None:
        """Mark node as stable."""
        self.status = EnumMetadataNodeStatus.STABLE
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    def validate_node(self) -> None:
        """Mark node as validated."""
        self.last_validated = datetime.now(UTC)

    def record_usage(
        self,
        success: bool,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Record node usage."""
        self.usage_metrics.record_invocation(
            success,
            execution_time_ms,
            memory_usage_mb,
        )
        self.update_timestamp()

    def set_documentation_quality(self, quality: EnumValidationLevel) -> None:
        """Set documentation quality level."""
        valid_levels = [
            EnumValidationLevel.BASIC,
            EnumValidationLevel.STANDARD,
            EnumValidationLevel.COMPREHENSIVE,
        ]
        if quality in valid_levels:
            self.documentation_quality = quality
            self.has_documentation = True
            self.update_timestamp()

    def add_custom_metadata(self, key: str, value: ModelMetadataValue) -> None:
        """Add custom metadata using strongly-typed value."""
        # Use the already typed metadata value directly
        self.custom_metadata[key] = ModelValue.from_any(value.to_python_value())
        self.update_timestamp()

    def get_custom_metadata(
        self,
        key: str,
        default: ModelValue | None = None,
    ) -> ModelValue | None:
        """Get custom metadata value."""
        return self.custom_metadata.get(key, default)

    def to_summary(self) -> ModelNodeInfoSummary:
        """Get node summary with clean typing."""
        # Convert enum types to match ModelNodeInfoSummary expectations
        from omnibase_core.enums.enum_documentation_quality import (
            EnumDocumentationQuality,
        )
        from omnibase_core.enums.enum_node_type import EnumNodeType

        # Map node type (compare enum directly)
        node_type = (
            EnumNodeType.FUNCTION
            if self.node_type == EnumMetadataNodeType.FUNCTION
            else EnumNodeType.UNKNOWN
        )

        # Map documentation quality (using quality level enum keys)
        doc_quality_map = {
            EnumValidationLevel.BASIC: EnumDocumentationQuality.MINIMAL,
            EnumValidationLevel.STANDARD: EnumDocumentationQuality.GOOD,
            EnumValidationLevel.COMPREHENSIVE: EnumDocumentationQuality.COMPREHENSIVE,
        }
        documentation_quality = doc_quality_map.get(
            self.documentation_quality,
            EnumDocumentationQuality.NONE,
        )

        summary = ModelNodeInfoSummary()

        # Set core properties
        summary.core.node_id = self.node_id
        summary.core.node_display_name = self.display_name.display_name
        summary.core.description = self.description.summary_description
        summary.core.node_type = node_type
        summary.core.version = self.version

        # Set timestamps
        summary.timestamps.created_at = self.created_at
        summary.timestamps.updated_at = self.updated_at
        summary.timestamps.last_validated = self.last_validated

        # Set categorization
        summary.categorization.tags = self.tags.all_tags
        summary.categorization.categories = [
            cat
            for cat in [self.tags.primary_category] + self.tags.secondary_categories
            if cat is not None
        ]
        summary.categorization.dependencies = self.dependencies
        summary.categorization.related_nodes = self.related_nodes

        # Set quality indicators
        summary.quality.has_documentation = self.has_documentation
        summary.quality.has_examples = self.has_examples
        summary.quality.documentation_quality = documentation_quality

        # Set performance metrics
        summary.performance.usage_count = self.usage_metrics.total_invocations
        summary.performance.success_rate = self.get_success_rate()
        summary.performance.error_rate = 1.0 - self.get_success_rate()
        summary.performance.average_execution_time_ms = (
            self.usage_metrics.average_execution_time_ms
        )
        summary.performance.memory_usage_mb = self.usage_metrics.peak_memory_usage_mb

        return summary

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str = "",
        node_type: EnumMetadataNodeType = EnumMetadataNodeType.FUNCTION,
    ) -> ModelMetadataNodeInfo:
        """Create a simple node info."""
        import hashlib

        # Generate UUID from name
        node_hash = hashlib.sha256(name.encode()).hexdigest()
        node_id = UUID(
            f"{node_hash[:8]}-{node_hash[8:12]}-{node_hash[12:16]}-{node_hash[16:20]}-{node_hash[20:32]}",
        )

        display_name = ModelStructuredDisplayName.for_metadata_node(name)
        structured_description = ModelStructuredDescription.for_metadata_node(
            name,
            functionality=description,
        )
        tags = ModelStructuredTags.for_metadata_node()

        return cls(
            node_id=node_id,
            display_name=display_name,
            description=structured_description,
            tags=tags,
            node_type=node_type,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def create_function_info(
        cls,
        name: str,
        description: str = "",
        complexity: EnumConceptualComplexity = EnumConceptualComplexity.BASIC,
    ) -> ModelMetadataNodeInfo:
        """Create function node info."""

        # Generate UUID from name
        node_hash = hashlib.sha256(name.encode()).hexdigest()
        node_id = UUID(
            f"{node_hash[:8]}-{node_hash[8:12]}-{node_hash[12:16]}-{node_hash[16:20]}-{node_hash[20:32]}",
        )

        display_name = ModelStructuredDisplayName.for_metadata_node(
            name,
            category=EnumStandardCategory.BUSINESS_LOGIC,
        )
        structured_description = ModelStructuredDescription.for_metadata_node(
            name,
            functionality=description,
            category=EnumStandardCategory.BUSINESS_LOGIC,
        )

        # Map complexity to standard tag
        complexity_tag = None
        if (
            complexity == EnumConceptualComplexity.TRIVIAL
            or complexity == EnumConceptualComplexity.BASIC
        ):
            complexity_tag = EnumStandardTag.SIMPLE
        elif complexity == EnumConceptualComplexity.INTERMEDIATE:
            complexity_tag = EnumStandardTag.MODERATE
        elif complexity == EnumConceptualComplexity.ADVANCED:
            complexity_tag = EnumStandardTag.COMPLEX
        elif complexity == EnumConceptualComplexity.EXPERT:
            complexity_tag = EnumStandardTag.ADVANCED

        tags = ModelStructuredTags.for_metadata_node(
            complexity=complexity_tag,
            domain=EnumStandardTag.API,
        )

        return cls(
            node_id=node_id,
            display_name=display_name,
            description=structured_description,
            tags=tags,
            node_type=EnumMetadataNodeType.FUNCTION,
            complexity=complexity,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

    @classmethod
    def create_documentation_info(
        cls,
        name: str,
        description: str = "",
    ) -> ModelMetadataNodeInfo:
        """Create documentation node info."""

        # Generate UUID from name
        node_hash = hashlib.sha256(name.encode()).hexdigest()
        node_id = UUID(
            f"{node_hash[:8]}-{node_hash[8:12]}-{node_hash[12:16]}-{node_hash[16:20]}-{node_hash[20:32]}",
        )

        display_name = ModelStructuredDisplayName.for_metadata_node(
            name,
            category=EnumStandardCategory.DOCUMENTATION,
        )
        structured_description = ModelStructuredDescription.for_metadata_node(
            name,
            functionality=description,
            category=EnumStandardCategory.DOCUMENTATION,
        )
        tags = ModelStructuredTags.for_metadata_node(
            complexity=EnumStandardTag.SIMPLE,
            domain=EnumStandardTag.DOCUMENTED,
        )

        return cls(
            node_id=node_id,
            display_name=display_name,
            description=structured_description,
            tags=tags,
            node_type=EnumMetadataNodeType.DOCUMENTATION,
            has_documentation=True,
            documentation_quality=EnumValidationLevel.STANDARD,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        display_name = self.display_name.display_name
        if display_name:
            result["name"] = display_name
        description = self.description.summary_description
        if description:
            result["description"] = description
        result["version"] = self.version
        all_tags = self.tags.all_tags
        if all_tags:
            result["tags"] = all_tags
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If metadata setting logic fails
        """
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = [
    "ModelMetadataNodeComplexity",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeStatus",
    "ModelMetadataNodeType",
    "ModelMetadataUsageMetrics",
]
