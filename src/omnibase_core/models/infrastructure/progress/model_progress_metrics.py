"""
Progress Metrics Model.

Custom metrics and tagging for progress tracking.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_metrics_data import ModelMetricsData
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelProgressMetrics(BaseModel):
    """
    Progress metrics with custom data and tagging support.

    Focused on extensible metrics tracking and categorization.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Metadata
    custom_metrics: ModelMetricsData = Field(
        default_factory=lambda: ModelMetricsData(
            collection_id=None,
            collection_display_name=ModelSchemaValue.from_value("progress_metrics"),
        ),
        description="Custom progress metrics with clean typing",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Progress tracking tags",
    )

    # Metrics timestamps
    metrics_last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last metrics update timestamp",
    )

    def add_custom_metric(self, key: str, value: object) -> None:
        """Add custom progress metric with flexible typing (accepts ModelFlexibleValue or plain values)."""
        self.custom_metrics.add_metric(key, value)
        self.metrics_last_updated = datetime.now(UTC)

    def get_custom_metric(self, key: str) -> ModelFlexibleValue | None:
        """Get custom metric value."""
        raw_value = self.custom_metrics.get_metric_by_key(key)
        if raw_value is not None:
            return ModelFlexibleValue.from_any(raw_value, source="progress_metrics")
        return None

    def remove_custom_metric(self, key: str) -> bool:
        """Remove custom metric. Returns True if metric existed."""
        existed = key in self.custom_metrics.get_all_keys()
        if existed:
            # Remove metric by filtering the list
            self.custom_metrics.metrics = [
                metric for metric in self.custom_metrics.metrics if metric.key != key
            ]
            self.metrics_last_updated = datetime.now(UTC)
        return existed

    def add_tag(self, tag: str) -> None:
        """Add a progress tag."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.metrics_last_updated = datetime.now(UTC)

    def remove_tag(self, tag: str) -> bool:
        """Remove a progress tag. Returns True if tag existed."""
        try:
            self.tags.remove(tag)
            self.metrics_last_updated = datetime.now(UTC)
            return True
        except ValueError:
            return False

    def has_tag(self, tag: str) -> bool:
        """Check if progress has a specific tag."""
        return tag in self.tags

    def add_tags(self, tags: list[str]) -> None:
        """Add multiple tags."""
        for tag in tags:
            self.add_tag(tag)

    def remove_tags(self, tags: list[str]) -> list[str]:
        """Remove multiple tags. Returns list[Any]of tags that were actually removed."""
        removed = []
        for tag in tags:
            if self.remove_tag(tag):
                removed.append(tag)
        return removed

    def clear_tags(self) -> None:
        """Clear all tags."""
        if self.tags:
            self.tags.clear()
            self.metrics_last_updated = datetime.now(UTC)

    def get_tags_count(self) -> int:
        """Get count of tags."""
        return len(self.tags)

    def get_metrics_count(self) -> int:
        """Get count of custom metrics."""
        return len(self.custom_metrics.metrics)

    def has_custom_metrics(self) -> bool:
        """Check if any custom metrics exist."""
        return self.get_metrics_count() > 0

    def get_metrics_summary(self) -> dict[str, ModelFlexibleValue]:
        """Get summary of all custom metrics."""
        summary = {}
        for key in self.custom_metrics.get_all_keys():
            metric_value = self.get_custom_metric(key)
            if metric_value is not None:
                summary[key] = metric_value
        return summary

    def update_standard_metrics(
        self,
        percentage: float,
        current_step: int,
        total_steps: int,
        is_completed: bool,
        elapsed_seconds: float,
    ) -> None:
        """Update standard progress metrics with plain values (automatically converted to appropriate types)."""
        self.add_custom_metric("percentage", percentage)
        self.add_custom_metric("current_step", current_step)
        self.add_custom_metric("total_steps", total_steps)
        self.add_custom_metric("is_completed", is_completed)
        self.add_custom_metric("elapsed_seconds", elapsed_seconds)

    def reset(self) -> None:
        """Reset all metrics and tags."""
        self.custom_metrics.clear_all_metrics()
        self.tags.clear()
        self.metrics_last_updated = datetime.now(UTC)

    def reset_metrics_only(self) -> None:
        """Reset only custom metrics, keep tags."""
        self.custom_metrics.clear_all_metrics()
        self.metrics_last_updated = datetime.now(UTC)

    def reset_tags_only(self) -> None:
        """Reset only tags, keep custom metrics."""
        self.tags.clear()
        self.metrics_last_updated = datetime.now(UTC)

    @classmethod
    def create_with_tags(cls, tags: list[str]) -> ModelProgressMetrics:
        """Create metrics instance with initial tags."""
        return cls(tags=tags.copy())

    @classmethod
    def create_with_metrics(
        cls,
        initial_metrics: dict[str, object],
    ) -> ModelProgressMetrics:
        """Create metrics instance with initial custom metrics (accepts ModelFlexibleValue or plain values)."""
        instance = cls()
        for key, value in initial_metrics.items():
            instance.add_custom_metric(key, value)
        return instance

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    async def execute(self) -> object:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Return current state as execution result
            return self.model_dump(exclude_none=False, by_alias=True)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> None:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# NOTE: model_rebuild() removed - Pydantic v2 handles forward references automatically
# Even though ModelMetadataValue is imported directly (not under TYPE_CHECKING),
# explicit rebuilds at module level can cause import order issues
# Pydantic will rebuild the model lazily when first accessed

# Export for use
__all__ = ["ModelProgressMetrics"]
