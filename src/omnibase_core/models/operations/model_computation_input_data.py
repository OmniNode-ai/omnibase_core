"""
Strongly-typed computation input data model.

Replaces dict[str, Any] usage in computation input operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_binary_computation_input import (
    ModelBinaryComputationInput,
)
from omnibase_core.models.operations.model_computation_metadata_context import (
    ModelComputationMetadataContext,
)
from omnibase_core.models.operations.model_numeric_computation_input import (
    ModelNumericComputationInput,
)
from omnibase_core.models.operations.model_structured_computation_input import (
    ModelStructuredComputationInput,
)
from omnibase_core.models.operations.model_text_computation_input import (
    ModelTextComputationInput,
)

# Import discriminated union types
ModelComputationInputUnion = Annotated[
    ModelNumericComputationInput
    | ModelTextComputationInput
    | ModelBinaryComputationInput
    | ModelStructuredComputationInput,
    Field(discriminator="computation_type"),
]


class ModelComputationInputData(BaseModel):
    """
    Strongly-typed input data for computation operations with discriminated unions.

    Replaces primitive soup pattern with discriminated data types.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    computation_type: EnumComputationType = Field(
        default=...,
        description="Type of computation being performed",
    )
    input_data: ModelComputationInputUnion = Field(
        default=...,
        description="Computation-specific input data with discriminated union",
    )
    metadata_context: ModelComputationMetadataContext = Field(
        default_factory=ModelComputationMetadataContext,
        description="Structured metadata context for computation",
    )

    @field_validator("input_data")
    @classmethod
    def validate_input_data_type(
        cls,
        v: ModelComputationInputUnion,
        info: ValidationInfo,
    ) -> ModelComputationInputUnion:
        """Validate that input_data type matches computation_type discriminator."""
        if "computation_type" not in info.data:
            return v

        computation_type = info.data["computation_type"]

        if computation_type == EnumComputationType.NUMERIC and not isinstance(
            v,
            ModelNumericComputationInput,
        ):
            raise ModelOnexError(
                message="NUMERIC computation_type requires ModelNumericComputationInput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if computation_type == EnumComputationType.TEXT and not isinstance(
            v,
            ModelTextComputationInput,
        ):
            raise ModelOnexError(
                message="TEXT computation_type requires ModelTextComputationInput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if computation_type == EnumComputationType.BINARY and not isinstance(
            v,
            ModelBinaryComputationInput,
        ):
            raise ModelOnexError(
                message="BINARY computation_type requires ModelBinaryComputationInput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if computation_type == EnumComputationType.STRUCTURED and not isinstance(
            v,
            ModelStructuredComputationInput,
        ):
            raise ModelOnexError(
                message="STRUCTURED computation_type requires ModelStructuredComputationInput",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelComputationInputData", "ModelComputationInputUnion"]
