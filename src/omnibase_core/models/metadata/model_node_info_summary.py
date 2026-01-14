"""
Node Info Summary Model (Composed).

Composed model that combines focused node information components.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_documentation_quality import EnumDocumentationQuality
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_categorization_update_data import (
    TypedDictCategorizationUpdateData,
)
from omnibase_core.types.typed_dict_node_core_update_data import (
    TypedDictNodeCoreUpdateData,
)
from omnibase_core.types.typed_dict_node_info_summary_data import (
    TypedDictNodeInfoSummaryData,
)
from omnibase_core.types.typed_dict_performance_update_data import (
    TypedDictPerformanceUpdateData,
)
from omnibase_core.types.typed_dict_quality_update_data import (
    TypedDictQualityUpdateData,
)
from omnibase_core.types.typed_dict_timestamp_update_data import (
    TypedDictTimestampUpdateData,
)

from .node_info.model_node_categorization import ModelNodeCategorization
from .node_info.model_node_core import ModelNodeCore
from .node_info.model_node_performance_metrics import ModelNodePerformanceMetrics
from .node_info.model_node_quality_indicators import ModelNodeQualityIndicators
from .node_info.model_node_timestamps import ModelNodeTimestamps


class ModelNodeInfoSummary(BaseModel):
    """
    Composed node info summary using focused components.

    Provides comprehensive node information with core data, timing,
    categorization, quality indicators, and performance metrics.
    """

    # Composed components
    core: ModelNodeCore = Field(
        default_factory=lambda: ModelNodeCore(
            node_display_name=None,
            description=None,
        ),
        description="Core node identification and basic information",
    )
    timestamps: ModelNodeTimestamps = Field(
        default_factory=lambda: ModelNodeTimestamps(
            created_at=None,
            updated_at=None,
            last_validated=None,
        ),
        description="Timing and lifecycle information",
    )
    categorization: ModelNodeCategorization = Field(
        default_factory=ModelNodeCategorization,
        description="Categories, tags, and relationships",
    )
    quality: ModelNodeQualityIndicators = Field(
        default_factory=ModelNodeQualityIndicators,
        description="Quality and documentation indicators",
    )
    performance: ModelNodePerformanceMetrics = Field(
        default_factory=ModelNodePerformanceMetrics,
        description="Usage and performance metrics",
    )

    # Properties for direct access
    @property
    def node_id(self) -> UUID:
        return self.core.node_id

    @node_id.setter
    def node_id(self, value: UUID) -> None:
        self.core.node_id = value

    @property
    def node_display_name(self) -> str | None:
        return self.core.node_display_name

    @node_display_name.setter
    def node_display_name(self, value: str | None) -> None:
        self.core.node_display_name = value

    @property
    def description(self) -> str | None:
        return self.core.description

    @description.setter
    def description(self, value: str | None) -> None:
        self.core.description = value

    @property
    def node_type(self) -> EnumNodeType:
        return self.core.node_type

    @node_type.setter
    def node_type(self, value: EnumNodeType) -> None:
        self.core.node_type = value

    @property
    def status(self) -> EnumMetadataNodeStatus:
        return self.core.status

    @status.setter
    def status(self, value: EnumMetadataNodeStatus) -> None:
        self.core.status = value

    @property
    def complexity(self) -> EnumConceptualComplexity:
        return self.core.complexity

    @complexity.setter
    def complexity(self, value: EnumConceptualComplexity) -> None:
        self.core.complexity = value

    @property
    def version(self) -> ModelSemVer:
        return self.core.version

    @version.setter
    def version(self, value: ModelSemVer) -> None:
        self.core.version = value

    @property
    def created_at(self) -> datetime | None:
        return self.timestamps.created_at

    @created_at.setter
    def created_at(self, value: datetime | None) -> None:
        self.timestamps.created_at = value

    @property
    def updated_at(self) -> datetime | None:
        return self.timestamps.updated_at

    @updated_at.setter
    def updated_at(self, value: datetime | None) -> None:
        self.timestamps.updated_at = value

    @property
    def last_validated(self) -> datetime | None:
        return self.timestamps.last_validated

    @last_validated.setter
    def last_validated(self, value: datetime | None) -> None:
        self.timestamps.last_validated = value

    @property
    def tags(self) -> list[str]:
        return self.categorization.tags

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.categorization.tags = value.copy()

    @property
    def categories(self) -> list[str]:
        return self.categorization.categories

    @categories.setter
    def categories(self, value: list[str]) -> None:
        self.categorization.categories = value.copy()

    @property
    def dependencies(self) -> list[UUID]:
        return self.categorization.dependencies

    @dependencies.setter
    def dependencies(self, value: list[UUID]) -> None:
        self.categorization.dependencies = value.copy()

    @property
    def related_nodes(self) -> list[UUID]:
        return self.categorization.related_nodes

    @related_nodes.setter
    def related_nodes(self, value: list[UUID]) -> None:
        self.categorization.related_nodes = value.copy()

    @property
    def has_documentation(self) -> bool:
        return self.quality.has_documentation

    @has_documentation.setter
    def has_documentation(self, value: bool) -> None:
        self.quality.has_documentation = value

    @property
    def has_examples(self) -> bool:
        return self.quality.has_examples

    @has_examples.setter
    def has_examples(self, value: bool) -> None:
        self.quality.has_examples = value

    @property
    def documentation_quality(self) -> EnumDocumentationQuality:
        return self.quality.documentation_quality

    @documentation_quality.setter
    def documentation_quality(self, value: EnumDocumentationQuality) -> None:
        self.quality.documentation_quality = value

    @property
    def usage_count(self) -> int:
        return self.performance.usage_count

    @usage_count.setter
    def usage_count(self, value: int) -> None:
        self.performance.usage_count = value

    @property
    def success_rate(self) -> float:
        return self.performance.success_rate

    @success_rate.setter
    def success_rate(self, value: float) -> None:
        self.performance.success_rate = value

    @property
    def error_rate(self) -> float:
        return self.performance.error_rate

    @error_rate.setter
    def error_rate(self, value: float) -> None:
        self.performance.error_rate = value

    @property
    def average_execution_time_ms(self) -> float:
        return self.performance.average_execution_time_ms

    @average_execution_time_ms.setter
    def average_execution_time_ms(self, value: float) -> None:
        self.performance.average_execution_time_ms = value

    @property
    def memory_usage_mb(self) -> float:
        return self.performance.memory_usage_mb

    @memory_usage_mb.setter
    def memory_usage_mb(self, value: float) -> None:
        self.performance.memory_usage_mb = value

    # Composite methods
    def get_comprehensive_summary(self) -> TypedDictNodeInfoSummaryData:
        """Get comprehensive summary from all components."""
        return {
            "core": {
                "node_id": self.core.node_id,
                "node_display_name": self.core.node_display_name,
                "description": self.core.description,
                "node_type": self.core.node_type.value,
                "status": self.core.status.value,
                "complexity": self.core.complexity.value,
                "version": self.core.version,
                "is_active": self.core.is_active,
                "is_complex": self.core.is_complex,
            },
            "timestamps": self.timestamps.get_lifecycle_summary(),
            "categorization": self.categorization.get_categorization_summary(),
            "quality": self.quality.get_quality_summary().model_dump(),
            "performance": self.performance.get_performance_summary().model_dump(),
        }

    def update_all_metrics(
        self,
        core_data: TypedDictNodeCoreUpdateData | None = None,
        timestamp_data: TypedDictTimestampUpdateData | None = None,
        categorization_data: TypedDictCategorizationUpdateData | None = None,
        quality_data: TypedDictQualityUpdateData | None = None,
        performance_data: TypedDictPerformanceUpdateData | None = None,
    ) -> None:
        """
        Update all component metrics with structured typing.

        Args:
            core_data: Core node data with string and enum values
            timestamp_data: Timestamp data with datetime values
            categorization_data: Categorization data with string list[Any]s
            quality_data: Quality data with float and enum values
            performance_data: Performance data with numeric values

        Note:
            All parameters are optional and use typed dict[str, Any]ionaries for type safety.
        """

        # Update core data
        if core_data:
            if "node_display_name" in core_data:
                value = core_data["node_display_name"]
                self.core.node_display_name = str(value) if value is not None else None
            if "description" in core_data:
                value = core_data["description"]
                self.core.description = str(value) if value is not None else None
            if "status" in core_data:
                from omnibase_core.enums.enum_metadata_node_status import (
                    EnumMetadataNodeStatus,
                )

                value = core_data["status"]
                if isinstance(value, EnumMetadataNodeStatus):
                    self.core.update_status(value)
            if "complexity" in core_data:
                value = core_data["complexity"]
                if isinstance(value, EnumConceptualComplexity):
                    self.core.update_complexity(value)

        # Update timestamps
        if timestamp_data:
            if "created_at" in timestamp_data:
                self.timestamps.update_created_timestamp(timestamp_data["created_at"])
            if "updated_at" in timestamp_data:
                self.timestamps.update_modified_timestamp(timestamp_data["updated_at"])
            if "last_accessed" in timestamp_data:
                self.timestamps.update_validation_timestamp(
                    timestamp_data["last_accessed"],
                )

        # Update categorization
        if categorization_data:
            if "technical_tags" in categorization_data:
                self.categorization.add_tags(categorization_data["technical_tags"])
            if "business_tags" in categorization_data:
                self.categorization.add_tags(categorization_data["business_tags"])

        # Update quality
        if quality_data:
            if any(
                key in quality_data
                for key in [
                    "has_documentation",
                    "documentation_quality",
                    "has_examples",
                ]
            ):
                # Extract and validate documentation status parameters
                has_doc_value = quality_data.get(
                    "has_documentation",
                    self.quality.has_documentation,
                )
                doc_quality_value = quality_data.get("documentation_quality")
                has_examples_value = quality_data.get("has_examples")

                # Type check and convert values
                has_doc = (
                    bool(has_doc_value)
                    if has_doc_value is not None
                    else self.quality.has_documentation
                )

                doc_quality = None
                if doc_quality_value is not None:
                    from omnibase_core.enums.enum_documentation_quality import (
                        EnumDocumentationQuality,
                    )

                    if isinstance(doc_quality_value, EnumDocumentationQuality):
                        doc_quality = doc_quality_value

                has_examples = None
                if has_examples_value is not None:
                    has_examples = bool(has_examples_value)

                self.quality.update_documentation_status(
                    has_doc,
                    doc_quality,
                    has_examples,
                )

        # Update performance
        if performance_data:
            if any(
                key in performance_data
                for key in ["usage_count", "success_rate", "error_rate"]
            ):
                usage_value = performance_data.get(
                    "usage_count",
                    self.performance.usage_count,
                )
                success_value = performance_data.get(
                    "success_rate",
                    self.performance.success_rate,
                )
                error_value = performance_data.get(
                    "error_rate",
                    self.performance.error_rate,
                )

                self.performance.update_usage_metrics(
                    (
                        int(usage_value)
                        if isinstance(usage_value, (int, str))
                        else self.performance.usage_count
                    ),
                    (
                        float(success_value)
                        if isinstance(success_value, (int, float, str))
                        else self.performance.success_rate
                    ),
                    (
                        float(error_value)
                        if isinstance(error_value, (int, float, str))
                        else self.performance.error_rate
                    ),
                )
            if any(
                key in performance_data
                for key in ["average_execution_time_ms", "memory_usage_mb"]
            ):
                self.performance.update_performance_metrics(
                    performance_data.get(
                        "average_execution_time_ms",
                        self.performance.average_execution_time_ms,
                    ),
                    performance_data.get(
                        "memory_usage_mb",
                        self.performance.memory_usage_mb,
                    ),
                )

    def is_healthy(self) -> bool:
        """Check if node is healthy overall."""
        return (
            self.core.is_active
            and not self.timestamps.is_stale()
            and self.quality.get_quality_score() > 60.0
            and not self.performance.has_performance_issues
        )

    def get_health_score(self) -> float:
        """Calculate composite health score (0-100)."""
        # Status score (25% weight)
        status_score = 25.0 if self.core.is_active else 0.0

        # Freshness score (25% weight)
        if self.timestamps.is_recently_updated():
            freshness_score = 25.0
        elif self.timestamps.is_stale():
            freshness_score = 5.0
        else:
            freshness_score = 15.0

        # Quality score (25% weight)
        quality_score = self.quality.get_quality_score() * 0.25

        # Performance score (25% weight)
        performance_score = self.performance.calculate_performance_score() * 0.25

        return status_score + freshness_score + quality_score + performance_score

    @classmethod
    def create_for_node(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: EnumNodeType,
        description: str | None = None,
    ) -> ModelNodeInfoSummary:
        """Create node info summary for specific node."""
        core = ModelNodeCore.create_for_node(node_id, node_name, node_type, description)
        timestamps = ModelNodeTimestamps.create_new()
        return cls(core=core, timestamps=timestamps)

    @classmethod
    def create_well_documented_node(
        cls,
        node_name: str,
        node_type: EnumNodeType,
        tags: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> ModelNodeInfoSummary:
        """Create node info summary with excellent quality."""
        core = ModelNodeCore.create_minimal_node(node_name, node_type)
        timestamps = ModelNodeTimestamps.create_new()
        categorization = ModelNodeCategorization.create_comprehensive(
            tags if tags is not None else [],
            categories if categories is not None else [],
        )
        quality = ModelNodeQualityIndicators.create_excellent_quality()
        performance = ModelNodePerformanceMetrics.create_high_performance()

        return cls(
            core=core,
            timestamps=timestamps,
            categorization=categorization,
            quality=quality,
            performance=performance,
        )

    @classmethod
    def create_minimal_node(
        cls,
        node_name: str,
        node_type: EnumNodeType = EnumNodeType.UNKNOWN,
    ) -> ModelNodeInfoSummary:
        """Create minimal node info summary."""
        core = ModelNodeCore.create_minimal_node(node_name, node_type)
        timestamps = ModelNodeTimestamps.create_new()
        return cls(core=core, timestamps=timestamps)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        if self.node_display_name:
            result["name"] = self.node_display_name
        if self.description:
            result["description"] = self.description
        # version has default_factory in ModelNodeCore, always present
        result["version"] = self.version
        if self.tags:
            result["tags"] = self.tags
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


__all__ = ["ModelNodeInfoSummary"]
