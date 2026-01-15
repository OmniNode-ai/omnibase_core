"""
Metrics data model.

Clean, strongly-typed replacement for custom metrics union types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

# Union import removed - using strongly-typed discriminated unions
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_flexible_value_type import EnumFlexibleValueType
from omnibase_core.enums.enum_metric_data_type import EnumMetricDataType
from omnibase_core.enums.enum_metrics_category import EnumMetricsCategory

# Import from common layer instead of metadata layer to avoid circular dependency
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_metric import ModelMetric


class ModelMetricsData(BaseModel):
    """
    Clean, strongly-typed model replacing custom metrics union types.

    Eliminates: dict[str, str | int | bool | float]

    With proper structured data using a single generic metric type.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Single list[Any]of universal metrics using discriminated union pattern
    metrics: list[ModelMetric] = Field(
        default_factory=list,
        description="Collection of typed metrics",
    )

    # Metadata
    collection_id: UUID | None = Field(
        default=None, description="UUID for metrics collection"
    )
    collection_display_name: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Human-readable name of the metrics collection",
    )

    category: EnumMetricsCategory = Field(
        default=EnumMetricsCategory.GENERAL,
        description="Category of metrics",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for organizing metrics",
    )

    def add_metric(
        self,
        key: str,
        value: object,
        description: str | None = None,
        unit: str | None = None,
    ) -> None:
        """Add a metric with bounded type values."""
        metric = ModelMetric.from_any_value(
            key=key,
            value=value,
            unit=unit,
            description=description,
        )
        self.metrics.append(metric)

    def get_metric_by_key(self, key: str) -> ModelFlexibleValue | None:
        """Get metric value by key with bounded return type."""
        for metric in self.metrics:
            if metric.key == key:
                return metric.value
        return None

    def get_all_keys(self) -> list[str]:
        """Get all metric keys."""
        return [metric.key for metric in self.metrics]

    def clear_all_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()

    def get_metrics_by_type(self, metric_type: EnumMetricDataType) -> list[ModelMetric]:
        """Get all metrics of a specific type."""
        type_mapping = {
            EnumMetricDataType.STRING: [EnumFlexibleValueType.STRING],
            EnumMetricDataType.NUMERIC: [
                EnumFlexibleValueType.INTEGER,
                EnumFlexibleValueType.FLOAT,
            ],
            EnumMetricDataType.BOOLEAN: [EnumFlexibleValueType.BOOLEAN],
        }
        valid_types = type_mapping[metric_type]
        return [
            metric for metric in self.metrics if metric.value.value_type in valid_types
        ]

    @property
    def collection_name(self) -> str | None:
        """Access collection name."""
        display_name_value = self.collection_display_name.to_value()
        if isinstance(display_name_value, str) and display_name_value:
            return display_name_value
        return None

    @collection_name.setter
    def collection_name(self, value: str | None) -> None:
        """Set collection name and generate corresponding ID."""
        if value:
            import hashlib

            collection_hash = hashlib.sha256(value.encode()).hexdigest()
            self.collection_id = UUID(
                f"{collection_hash[:8]}-{collection_hash[8:12]}-{collection_hash[12:16]}-{collection_hash[16:20]}-{collection_hash[20:32]}",
            )
        else:
            self.collection_id = None
        self.collection_display_name = ModelSchemaValue.from_value(
            value if value else "",
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# NOTE: model_rebuild() removed - Pydantic v2 handles forward references automatically
# The explicit rebuild at module level caused import failures because ModelMetadataValue
# is only available under TYPE_CHECKING guard to break circular imports
# Pydantic will rebuild the model lazily when first accessed

# Export for use
__all__ = ["ModelMetricsData"]
