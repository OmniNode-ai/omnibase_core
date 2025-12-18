"""
Metadata Analytics Summary Model (Composed).

Composed model that combines focused analytics components.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_analytics_summary_data import (
    TypedDictAnalyticsSummaryData,
)
from omnibase_core.types.typed_dict_core_data import TypedDictCoreData
from omnibase_core.types.typed_dict_error_data import TypedDictErrorData
from omnibase_core.types.typed_dict_performance_data import TypedDictPerformanceData
from omnibase_core.types.typed_dict_quality_data import TypedDictQualityData

from .analytics.model_analytics_core import ModelAnalyticsCore
from .analytics.model_analytics_error_tracking import ModelAnalyticsErrorTracking
from .analytics.model_analytics_performance_metrics import (
    ModelAnalyticsPerformanceMetrics,
)
from .analytics.model_analytics_quality_metrics import ModelAnalyticsQualityMetrics


class ModelMetadataAnalyticsSummary(BaseModel):
    """
    Composed analytics summary using focused components.

    Provides comprehensive analytics with collection info, quality metrics,
    error tracking, and performance data using composition pattern.
    """

    # Composed components
    core: ModelAnalyticsCore = Field(
        default_factory=lambda: ModelAnalyticsCore(collection_display_name=None),
        description="Core collection info and node counts",
    )
    quality: ModelAnalyticsQualityMetrics = Field(
        default_factory=ModelAnalyticsQualityMetrics,
        description="Quality and health metrics",
    )
    errors: ModelAnalyticsErrorTracking = Field(
        default_factory=ModelAnalyticsErrorTracking,
        description="Error and warning tracking",
    )
    performance: ModelAnalyticsPerformanceMetrics = Field(
        default_factory=ModelAnalyticsPerformanceMetrics,
        description="Performance and execution metrics",
    )

    # Timestamps
    last_modified: datetime | None = Field(
        default=None,
        description="Last modification timestamp",
    )
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Properties for direct access
    @property
    def collection_id(self) -> UUID:
        """Get collection ID."""
        return self.core.collection_id

    @collection_id.setter
    def collection_id(self, value: UUID) -> None:
        """Set collection ID."""
        self.core.collection_id = value

    @property
    def collection_display_name(self) -> str | None:
        """Get collection display name."""
        return self.core.collection_display_name

    @collection_display_name.setter
    def collection_display_name(self, value: str | None) -> None:
        """Set collection display name."""
        self.core.collection_display_name = value

    @property
    def collection_name(self) -> str | None:
        """Get collection name with fallback."""
        return self.core.collection_name

    @property
    def total_nodes(self) -> int:
        """Get total nodes."""
        return self.core.total_nodes

    @total_nodes.setter
    def total_nodes(self, value: int) -> None:
        """Set total nodes."""
        self.core.total_nodes = value

    @property
    def active_nodes(self) -> int:
        """Get active nodes."""
        return self.core.active_nodes

    @active_nodes.setter
    def active_nodes(self, value: int) -> None:
        """Set active nodes."""
        self.core.active_nodes = value

    @property
    def deprecated_nodes(self) -> int:
        """Get deprecated nodes."""
        return self.core.deprecated_nodes

    @deprecated_nodes.setter
    def deprecated_nodes(self, value: int) -> None:
        """Set deprecated nodes."""
        self.core.deprecated_nodes = value

    @property
    def disabled_nodes(self) -> int:
        """Get disabled nodes."""
        return self.core.disabled_nodes

    @disabled_nodes.setter
    def disabled_nodes(self, value: int) -> None:
        """Set disabled nodes."""
        self.core.disabled_nodes = value

    @property
    def health_score(self) -> float:
        """Get health score."""
        return self.quality.health_score

    @health_score.setter
    def health_score(self, value: float) -> None:
        """Set health score."""
        self.quality.health_score = value

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        return self.quality.success_rate

    @success_rate.setter
    def success_rate(self, value: float) -> None:
        """Set success rate."""
        self.quality.success_rate = value

    @property
    def documentation_coverage(self) -> float:
        """Get documentation coverage."""
        return self.quality.documentation_coverage

    @documentation_coverage.setter
    def documentation_coverage(self, value: float) -> None:
        """Set documentation coverage."""
        self.quality.documentation_coverage = value

    @property
    def error_count(self) -> int:
        """Get error count."""
        return self.errors.error_count

    @error_count.setter
    def error_count(self, value: int) -> None:
        """Set error count."""
        self.errors.error_count = value

    @property
    def warning_count(self) -> int:
        """Get warning count."""
        return self.errors.warning_count

    @warning_count.setter
    def warning_count(self, value: int) -> None:
        """Set warning count."""
        self.errors.warning_count = value

    @property
    def critical_error_count(self) -> int:
        """Get critical error count."""
        return self.errors.critical_error_count

    @critical_error_count.setter
    def critical_error_count(self, value: int) -> None:
        """Set critical error count."""
        self.errors.critical_error_count = value

    @property
    def average_execution_time_ms(self) -> float:
        """Get average execution time."""
        return self.performance.average_execution_time_ms

    @average_execution_time_ms.setter
    def average_execution_time_ms(self, value: float) -> None:
        """Set average execution time."""
        self.performance.average_execution_time_ms = value

    @property
    def peak_memory_usage_mb(self) -> float:
        """Get peak memory usage."""
        return self.performance.peak_memory_usage_mb

    @peak_memory_usage_mb.setter
    def peak_memory_usage_mb(self, value: float) -> None:
        """Set peak memory usage."""
        self.performance.peak_memory_usage_mb = value

    @property
    def total_invocations(self) -> int:
        """Get total invocations."""
        return self.performance.total_invocations

    @total_invocations.setter
    def total_invocations(self, value: int) -> None:
        """Set total invocations."""
        self.performance.total_invocations = value

    # Composite methods
    def update_all_metrics(
        self,
        core_data: TypedDictCoreData | None = None,
        quality_data: TypedDictQualityData | None = None,
        error_data: TypedDictErrorData | None = None,
        performance_data: TypedDictPerformanceData | None = None,
    ) -> None:
        """
        Update all component metrics with structured typing.

        Args:
            core_data: Core data with int values for node counts
            quality_data: Quality data with float values for metrics
            error_data: Error data with int values for error counts
            performance_data: Performance data with numeric values for metrics

        Note:
            All parameters are optional and use typed dict[str, Any]ionaries for type safety.
        """
        # Update core
        if core_data and "total_nodes" in core_data:
            self.core.update_node_counts(
                core_data.get("total_nodes", 0),
                core_data.get("active_nodes", 0),
                core_data.get("deprecated_nodes", 0),
                core_data.get("disabled_nodes", 0),
            )

        # Update quality
        if quality_data and any(
            key in quality_data
            for key in ["health_score", "success_rate", "documentation_coverage"]
        ):
            self.quality.update_quality_metrics(
                quality_data.get("health_score", self.quality.health_score),
                quality_data.get("success_rate", self.quality.success_rate),
                quality_data.get(
                    "documentation_coverage",
                    self.quality.documentation_coverage,
                ),
            )

        # Update errors
        if error_data and any(
            key in error_data
            for key in ["error_count", "warning_count", "critical_error_count"]
        ):
            self.errors.update_error_counts(
                error_data.get("error_count", self.errors.error_count),
                error_data.get("warning_count", self.errors.warning_count),
                error_data.get(
                    "critical_error_count",
                    self.errors.critical_error_count,
                ),
            )

        # Update performance
        if performance_data and any(
            key in performance_data
            for key in [
                "average_execution_time_ms",
                "peak_memory_usage_mb",
                "total_invocations",
            ]
        ):
            self.performance.update_performance_metrics(
                performance_data.get(
                    "average_execution_time_ms",
                    self.performance.average_execution_time_ms,
                ),
                performance_data.get(
                    "peak_memory_usage_mb",
                    self.performance.peak_memory_usage_mb,
                ),
                int(
                    performance_data.get(
                        "total_invocations",
                        self.performance.total_invocations,
                    ),
                ),
            )

    def get_comprehensive_summary(self) -> TypedDictAnalyticsSummaryData:
        """Get comprehensive summary from all components."""
        return {
            "core": {
                "collection_id": self.core.collection_id,
                "collection_name": self.core.collection_name,
                "total_nodes": self.core.total_nodes,
                "active_nodes": self.core.active_nodes,
                "deprecated_nodes": self.core.deprecated_nodes,
                "disabled_nodes": self.core.disabled_nodes,
                "has_issues": self.core.has_issues(),
            },
            "quality": self.quality.get_improvement_suggestions(),
            "errors": self.errors.get_error_summary(self.performance.total_invocations),
            "performance": self.performance.get_performance_summary(),
            "timestamps": {
                "last_modified": self.last_modified,
                "last_validated": self.last_validated,
            },
        }

    @classmethod
    def create_for_collection(
        cls,
        collection_id: UUID,
        collection_name: str,
    ) -> ModelMetadataAnalyticsSummary:
        """Create analytics summary for specific collection."""
        core = ModelAnalyticsCore.create_for_collection(collection_id, collection_name)
        return cls(
            core=core,
            last_modified=None,
            last_validated=None,
        )

    @classmethod
    def create_with_excellent_metrics(
        cls,
        collection_name: str,
    ) -> ModelMetadataAnalyticsSummary:
        """Create analytics summary with excellent metrics."""
        core = ModelAnalyticsCore.create_with_counts(
            collection_name=collection_name,
            total_nodes=100,
            active_nodes=95,
            deprecated_nodes=3,
            disabled_nodes=2,
        )
        quality = ModelAnalyticsQualityMetrics.create_excellent()
        errors = ModelAnalyticsErrorTracking.create_clean()
        performance = ModelAnalyticsPerformanceMetrics.create_fast()

        return cls(
            core=core,
            quality=quality,
            errors=errors,
            performance=performance,
            last_modified=None,
            last_validated=None,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata  # type: ignore[return-value]

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelMetadataAnalyticsSummary"]
