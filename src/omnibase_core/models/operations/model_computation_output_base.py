"""
Computation Output Base Model.

Base computation output with discriminator and common fields for all computation types.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.types.typed_dict_computation_output_summary import (
    TypedDictComputationOutputSummary,
)

if TYPE_CHECKING:
    from omnibase_core.enums.enum_computation_type import EnumComputationType


class ModelComputationOutputBase(BaseModel):
    """Base computation output with discriminator."""

    model_config = ConfigDict(from_attributes=True)

    computation_type: "EnumComputationType" = Field(
        default=...,
        description="Computation type discriminator",
    )
    computed_values: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Computed result values with proper typing",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric metrics from computation",
    )
    status_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean status indicators",
    )
    output_metadata: dict[str, str] = Field(
        default_factory=dict,
        description="String metadata about the results",
    )

    def add_computed_value(
        self, key: str, value: ModelSchemaValue
    ) -> "ModelComputationOutputBase":
        """Add a computed value to the results."""
        new_values = {**self.computed_values, key: value}
        return self.model_copy(update={"computed_values": new_values})

    def add_metric(self, key: str, value: float) -> "ModelComputationOutputBase":
        """Add a numeric metric."""
        new_metrics = {**self.metrics, key: value}
        return self.model_copy(update={"metrics": new_metrics})

    def set_status_flag(self, key: str, value: bool) -> "ModelComputationOutputBase":
        """Set a status flag."""
        new_flags = {**self.status_flags, key: value}
        return self.model_copy(update={"status_flags": new_flags})

    def add_metadata(self, key: str, value: str) -> "ModelComputationOutputBase":
        """Add output metadata."""
        new_metadata = {**self.output_metadata, key: value}
        return self.model_copy(update={"output_metadata": new_metadata})

    def has_computed_value(self, key: str) -> bool:
        """Check if a computed value exists."""
        return key in self.computed_values

    def get_computed_value(self, key: str) -> ModelSchemaValue | None:
        """Get a computed value by key."""
        return self.computed_values.get(key)

    def get_metric(self, key: str) -> float | None:
        """Get a metric value by key."""
        return self.metrics.get(key)

    def get_status_flag(self, key: str) -> bool | None:
        """Get a status flag by key."""
        return self.status_flags.get(key)

    def get_metadata(self, key: str) -> str | None:
        """Get metadata by key."""
        return self.output_metadata.get(key)

    def get_summary(self) -> TypedDictComputationOutputSummary:
        """Get a summary of the computation output."""
        return TypedDictComputationOutputSummary(
            computation_type=self.computation_type.value,
            computed_values_count=len(self.computed_values),
            metrics_count=len(self.metrics),
            status_flags_count=len(self.status_flags),
            metadata_count=len(self.output_metadata),
        )
