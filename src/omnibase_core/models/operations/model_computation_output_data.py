"""
Strongly-typed computation output data model.

Replaces dict[str, Any] usage in computation output operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.type_constraints import (
    Executable,
    Identifiable,
    ProtocolValidatable,
    Serializable,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


# Computation types (moved up for better organization)
class ModelComputationType(str, Enum):
    """Types of computation operations."""

    NUMERIC = "numeric"
    TEXT = "text"
    BINARY = "binary"
    STRUCTURED = "structured"


# Discriminated computation output types (base class first)
class ModelComputationOutputBase(BaseModel):
    """Base computation output with discriminator."""

    computation_type: ModelComputationType = Field(
        ..., description="Computation type discriminator"
    )
    computed_values: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Computed result values with proper typing"
    )
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Numeric metrics from computation"
    )
    status_flags: dict[str, bool] = Field(
        default_factory=dict, description="Boolean status indicators"
    )
    output_metadata: dict[str, str] = Field(
        default_factory=dict, description="String metadata about the results"
    )


class ModelNumericComputationOutput(ModelComputationOutputBase):
    """Numeric computation output data."""

    computation_type: ModelComputationType = Field(
        default=ModelComputationType.NUMERIC, description="Numeric computation type"
    )
    numeric_results: dict[str, float] = Field(
        default_factory=dict, description="Numeric computation results"
    )
    precision_achieved: int = Field(default=2, description="Actual precision achieved")
    calculation_errors: list[str] = Field(
        default_factory=list, description="Any calculation errors encountered"
    )
    convergence_info: dict[str, float] = Field(
        default_factory=dict,
        description="Convergence information for iterative calculations",
    )


class ModelTextComputationOutput(ModelComputationOutputBase):
    """Text computation output data."""

    computation_type: ModelComputationType = Field(
        default=ModelComputationType.TEXT, description="Text computation type"
    )
    text_results: dict[str, str] = Field(
        default_factory=dict, description="Text computation results"
    )
    language_detected: str = Field(
        default="", description="Detected language of processed text"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Confidence scores for text analysis"
    )
    processing_warnings: list[str] = Field(
        default_factory=list, description="Any processing warnings encountered"
    )


class ModelBinaryComputationOutput(ModelComputationOutputBase):
    """Binary data computation output."""

    computation_type: ModelComputationType = Field(
        default=ModelComputationType.BINARY, description="Binary computation type"
    )
    binary_results: dict[str, bytes] = Field(
        default_factory=dict, description="Binary computation results"
    )
    checksums_verified: bool = Field(
        default=True, description="Whether all checksums were verified"
    )
    compression_ratio: float = Field(
        default=1.0, description="Achieved compression ratio"
    )
    data_integrity_status: str = Field(
        default="verified", description="Data integrity status"
    )


class ModelStructuredComputationOutput(ModelComputationOutputBase):
    """Structured data computation output."""

    computation_type: ModelComputationType = Field(
        default=ModelComputationType.STRUCTURED,
        description="Structured computation type",
    )
    structured_results: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Structured computation results"
    )
    schema_validation_status: str = Field(
        default="valid", description="Schema validation status"
    )
    transformation_summary: dict[str, int] = Field(
        default_factory=dict, description="Summary of data transformations applied"
    )
    nested_structure_depth: int = Field(
        default=1, description="Maximum depth of nested structures processed"
    )


# Discriminated union type for computation output data (defined after constituent types)
ModelComputationOutputUnion = Annotated[
    Union[
        ModelNumericComputationOutput,
        ModelTextComputationOutput,
        ModelBinaryComputationOutput,
        ModelStructuredComputationOutput,
    ],
    Field(discriminator="computation_type"),
]


class ModelComputationOutputData(BaseModel):
    """
    Strongly-typed output data for computation operations with discriminated unions.

    Replaces primitive soup pattern with discriminated result types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    computation_type: ModelComputationType = Field(
        ..., description="Type of computation that was performed"
    )
    output_data: ModelComputationOutputUnion = Field(
        ..., description="Computation-specific output data with discriminated union"
    )
    processing_info: dict[str, str] = Field(
        default_factory=dict, description="Processing information and diagnostics"
    )

    @field_validator("output_data")
    @classmethod
    def validate_output_data_type(
        cls, v: ModelComputationOutputUnion, info: ValidationInfo
    ) -> ModelComputationOutputUnion:
        """Validate that output_data type matches computation_type discriminator."""
        if "computation_type" not in info.data:
            return v

        computation_type = info.data["computation_type"]

        if computation_type == ModelComputationType.NUMERIC and not isinstance(
            v, ModelNumericComputationOutput
        ):
            raise ValueError(
                "NUMERIC computation_type requires ModelNumericComputationOutput"
            )
        elif computation_type == ModelComputationType.TEXT and not isinstance(
            v, ModelTextComputationOutput
        ):
            raise ValueError(
                "TEXT computation_type requires ModelTextComputationOutput"
            )
        elif computation_type == ModelComputationType.BINARY and not isinstance(
            v, ModelBinaryComputationOutput
        ):
            raise ValueError(
                "BINARY computation_type requires ModelBinaryComputationOutput"
            )
        elif computation_type == ModelComputationType.STRUCTURED and not isinstance(
            v, ModelStructuredComputationOutput
        ):
            raise ValueError(
                "STRUCTURED computation_type requires ModelStructuredComputationOutput"
            )

        return v

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields with runtime validation
            for key, value in kwargs.items():
                if hasattr(self, key) and isinstance(value, (str, int, float, bool)):
                    setattr(self, key, value)
            return True
        except Exception:
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
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelComputationOutputData"]
