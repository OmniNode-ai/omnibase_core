"""
Structured Computation Output Model.

Structured data computation output with schema validation and transformation tracking.
"""

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_computation_output_base import (
    ModelComputationOutputBase,
)
from omnibase_core.types.typed_dict_structured_computation_summary import (
    TypedDictStructuredComputationSummary,
)


class ModelStructuredComputationOutput(ModelComputationOutputBase):
    """Structured data computation output."""

    computation_type: EnumComputationType = Field(
        default=EnumComputationType.STRUCTURED,
        description="Structured computation type",
    )
    structured_results: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Structured computation results",
    )
    schema_validation_status: str = Field(
        default="valid",
        description="Schema validation status",
    )
    transformation_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Summary of data transformations applied",
    )
    nested_structure_depth: int = Field(
        default=1,
        description="Maximum depth of nested structures processed",
    )

    def add_structured_result(
        self, key: str, value: ModelSchemaValue
    ) -> "ModelStructuredComputationOutput":
        """Add a structured result."""
        new_results = {**self.structured_results, key: value}
        return self.model_copy(update={"structured_results": new_results})

    def get_structured_result(self, key: str) -> ModelSchemaValue | None:
        """Get a structured result by key."""
        return self.structured_results.get(key)

    def set_schema_validation_status(
        self, status: str
    ) -> "ModelStructuredComputationOutput":
        """Set schema validation status."""
        return self.model_copy(update={"schema_validation_status": status})

    def is_schema_valid(self) -> bool:
        """Check if schema validation passed."""
        return self.schema_validation_status == "valid"

    def add_transformation_summary(
        self, key: str, count: int
    ) -> "ModelStructuredComputationOutput":
        """Add transformation summary entry."""
        new_summary = {**self.transformation_summary, key: count}
        return self.model_copy(update={"transformation_summary": new_summary})

    def get_transformation_count(self, transformation_type: str) -> int:
        """Get count for a specific transformation type."""
        return self.transformation_summary.get(transformation_type, 0)

    def set_nested_structure_depth(
        self, depth: int
    ) -> "ModelStructuredComputationOutput":
        """Set nested structure depth."""
        return self.model_copy(update={"nested_structure_depth": depth})

    def get_total_transformations(self) -> int:
        """Get total number of transformations applied."""
        return sum(self.transformation_summary.values())

    def get_complexity_score(self) -> float:
        """Get complexity score based on depth and transformations."""
        depth_score = self.nested_structure_depth * 10
        transformation_score = self.get_total_transformations() * 5
        return depth_score + transformation_score

    def get_structured_summary(self) -> TypedDictStructuredComputationSummary:
        """Get structured processing summary."""
        return TypedDictStructuredComputationSummary(
            result_count=len(self.structured_results),
            schema_valid=self.is_schema_valid(),
            validation_status=self.schema_validation_status,
            nested_depth=self.nested_structure_depth,
            total_transformations=self.get_total_transformations(),
            complexity_score=self.get_complexity_score(),
        )
