"""
Computation Output Data Model.

Strongly-typed output data for computation operations with discriminated unions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# NOTE: EnumComputationType must remain inside TYPE_CHECKING to avoid Pydantic
# discriminated union validation error at import time. The discriminated union
# in ModelComputationOutputUnion requires Literal types for discriminator fields,
# but the constituent models use EnumComputationType. Moving this import outside
# TYPE_CHECKING triggers the validation error during class definition.
# See: https://errors.pydantic.dev/2.12/u/discriminator-needs-literal
if TYPE_CHECKING:
    from omnibase_core.enums.enum_computation_type import EnumComputationType

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_binary_computation_output import (
    ModelBinaryComputationOutput,
)
from omnibase_core.models.operations.model_numeric_computation_output import (
    ModelNumericComputationOutput,
)
from omnibase_core.models.operations.model_structured_computation_output import (
    ModelStructuredComputationOutput,
)
from omnibase_core.models.operations.model_text_computation_output import (
    ModelTextComputationOutput,
)
from omnibase_core.types.typed_dict_computation_output_data_summary import (
    TypedDictComputationOutputDataSummary,
)

# Discriminated union type for computation output data (defined after constituent types)
ModelComputationOutputUnion = Annotated[
    ModelNumericComputationOutput
    | ModelTextComputationOutput
    | ModelBinaryComputationOutput
    | ModelStructuredComputationOutput,
    Field(discriminator="computation_type"),
]


class ModelComputationOutputData(BaseModel):
    """
    Strongly-typed output data for computation operations with discriminated unions.

    Replaces primitive soup pattern with discriminated result types.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    computation_type: EnumComputationType = Field(
        default=...,
        description="Type of computation that was performed",
    )
    output_data: ModelComputationOutputUnion = Field(
        default=...,
        description="Computation-specific output data with discriminated union",
    )
    processing_info: dict[str, str] = Field(
        default_factory=dict,
        description="Processing information and diagnostics",
    )

    @field_validator("output_data")
    @classmethod
    def validate_output_data_type(
        cls,
        v: ModelComputationOutputUnion,
        info: ValidationInfo,
    ) -> ModelComputationOutputUnion:
        """Validate that output_data type matches computation_type discriminator."""
        if "computation_type" not in info.data:
            return v

        computation_type = info.data["computation_type"]

        if computation_type == "numeric" and not isinstance(
            v,
            ModelNumericComputationOutput,
        ):
            raise ModelOnexError(
                message="NUMERIC computation_type requires ModelNumericComputationOutput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if computation_type == "text" and not isinstance(
            v,
            ModelTextComputationOutput,
        ):
            raise ModelOnexError(
                message="TEXT computation_type requires ModelTextComputationOutput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if computation_type == "binary" and not isinstance(
            v,
            ModelBinaryComputationOutput,
        ):
            raise ModelOnexError(
                message="BINARY computation_type requires ModelBinaryComputationOutput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if computation_type == "structured" and not isinstance(
            v,
            ModelStructuredComputationOutput,
        ):
            raise ModelOnexError(
                message="STRUCTURED computation_type requires ModelStructuredComputationOutput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields with runtime validation
            for key, value in kwargs.items():
                if hasattr(self, key) and isinstance(value, (str, int, float, bool)):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            message=f"{self.__class__.__name__} must have a valid ID field (type_id, id, uuid, identifier, etc.). Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        return True

    def add_processing_info(self, key: str, value: str) -> ModelComputationOutputData:
        """Add processing information."""
        new_info = {**self.processing_info, key: value}
        return self.model_copy(update={"processing_info": new_info})

    def get_processing_info(self, key: str) -> str | None:
        """Get processing information by key."""
        return self.processing_info.get(key)

    def get_output_summary(self) -> TypedDictComputationOutputDataSummary:
        """Get a comprehensive summary of the computation output."""
        base_summary = self.output_data.get_summary()
        return TypedDictComputationOutputDataSummary(
            computation_type=self.computation_type.value,
            computed_values_count=base_summary["computed_values_count"],
            metrics_count=base_summary["metrics_count"],
            status_flags_count=base_summary["status_flags_count"],
            metadata_count=base_summary["metadata_count"],
            processing_info_count=len(self.processing_info),
        )

    def is_successful(self) -> bool:
        """Check if computation was successful."""
        # Success criteria can be extended based on specific computation types
        if hasattr(self.output_data, "has_calculation_errors"):
            return not self.output_data.has_calculation_errors()
        if hasattr(self.output_data, "has_processing_warnings"):
            return not self.output_data.has_processing_warnings()
        if hasattr(self.output_data, "is_data_intact"):
            return self.output_data.is_data_intact()
        if hasattr(self.output_data, "is_schema_valid"):
            return self.output_data.is_schema_valid()
        return True  # Default to success if no specific criteria

    def get_error_count(self) -> int:
        """Get total error count from output data."""
        if hasattr(self.output_data, "has_calculation_errors"):
            calculation_errors = getattr(self.output_data, "calculation_errors", [])
            return len(calculation_errors)
        if hasattr(self.output_data, "has_processing_warnings"):
            processing_warnings = getattr(self.output_data, "processing_warnings", [])
            return len(processing_warnings)
        return 0
