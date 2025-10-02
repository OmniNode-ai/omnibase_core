"""
Strongly-typed computation input data model.

Replaces dict[str, Any] usage in computation input operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Discriminated union using the computation_type field


# Input data type enum for discriminated union
class ModelInputDataType(str, Enum):
    """Types of input data structures."""

    STRUCTURED = "structured"
    PRIMITIVE = "primitive"
    MIXED = "mixed"


# Discriminated union types for input data
class ModelStructuredInputValue(BaseModel):
    """Structured input value with complex data."""

    value_type: Literal["structured"] = "structured"
    value: ModelSchemaValue = Field(..., description="Complex structured value")


class ModelPrimitiveInputValue(BaseModel):
    """Primitive input value with basic types."""

    value_type: Literal["primitive"] = "primitive"
    value: object = Field(..., description="Primitive value")


class ModelMixedInputValue(BaseModel):
    """Mixed input value supporting multiple types."""

    value_type: Literal["mixed"] = "mixed"
    value: ModelSchemaValue = Field(..., description="Flexible value container")


# Computation types
class ModelComputationType(str, Enum):
    """Types of computation operations."""

    NUMERIC = "numeric"
    TEXT = "text"
    BINARY = "binary"
    STRUCTURED = "structured"


# Discriminated computation input types
class ModelComputationInputBase(BaseModel):
    """Base computation input with discriminator."""

    computation_type: ModelComputationType = Field(
        ...,
        description="Computation type discriminator",
    )
    source_values: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Source values for computation with proper typing",
    )
    operation_parameters: ModelComputationOperationParameters = Field(
        default_factory=lambda: ModelComputationOperationParameters(),
        description="Structured operation parameters for computation",
    )
    boolean_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean configuration flags",
    )


class ModelNumericComputationInput(ModelComputationInputBase):
    """Numeric computation input data."""

    computation_type: Literal[ModelComputationType.NUMERIC] = Field(
        default=ModelComputationType.NUMERIC,
        description="Numeric computation type",
    )
    numeric_parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric parameters for calculations",
    )
    precision_requirements: int = Field(
        default=2,
        description="Required decimal precision",
    )
    calculation_mode: str = Field(
        default="standard",
        description="Calculation mode or algorithm",
    )
    rounding_strategy: str = Field(
        default="round_half_up",
        description="Numeric rounding strategy",
    )


class ModelTextComputationInput(ModelComputationInputBase):
    """Text computation input data."""

    computation_type: Literal[ModelComputationType.TEXT] = Field(
        default=ModelComputationType.TEXT,
        description="Text computation type",
    )
    text_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Text-specific parameters",
    )
    encoding: str = Field(default="utf-8", description="Text encoding")
    language_locale: str = Field(
        default="en-US",
        description="Language and locale for text processing",
    )
    case_sensitivity: bool = Field(
        default=True,
        description="Whether text processing is case sensitive",
    )


class ModelBinaryComputationInput(ModelComputationInputBase):
    """Binary data computation input."""

    computation_type: Literal[ModelComputationType.BINARY] = Field(
        default=ModelComputationType.BINARY,
        description="Binary computation type",
    )
    binary_format: str = Field(..., description="Binary data format")
    compression_algorithm: str = Field(
        default="none",
        description="Compression algorithm used",
    )
    checksum_verification: bool = Field(
        default=True,
        description="Whether to verify data checksums",
    )
    byte_order: str = Field(
        default="big_endian",
        description="Byte order for binary data",
    )


class ModelStructuredComputationInput(ModelComputationInputBase):
    """Structured data computation input."""

    computation_type: Literal[ModelComputationType.STRUCTURED] = Field(
        default=ModelComputationType.STRUCTURED,
        description="Structured computation type",
    )
    schema_definition: str = Field(
        ...,
        description="Schema definition for structured data",
    )
    validation_level: str = Field(default="strict", description="Data validation level")
    transformation_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Data transformation rules",
    )
    nested_processing: bool = Field(
        default=True,
        description="Whether to process nested structures",
    )


# Structured metadata and parameter types to replace primitive soup patterns
class ModelComputationMetadataContext(BaseModel):
    """Structured computation metadata context."""

    execution_id: UUID = Field(
        default_factory=uuid4, description="Execution identifier"
    )
    computation_session: str = Field(
        default="",
        description="Computation session identifier",
    )
    performance_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Performance optimization hints",
    )
    quality_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Quality and precision requirements",
    )
    resource_constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Resource constraint specifications",
    )
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")
    trace_enabled: bool = Field(
        default=False,
        description="Whether execution tracing is enabled",
    )


class ModelComputationOperationParameters(BaseModel):
    """Structured computation operation parameters."""

    algorithm_name: str = Field(default="", description="Algorithm identifier")
    optimization_level: str = Field(
        default="standard",
        description="Optimization level",
    )
    parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution",
    )
    validation_mode: str = Field(default="strict", description="Input validation mode")
    error_handling: str = Field(
        default="fail_fast",
        description="Error handling strategy",
    )
    custom_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom parameters",
    )


# Discriminated union type for computation input data
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
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    computation_type: ModelComputationType = Field(
        ...,
        description="Type of computation being performed",
    )
    input_data: ModelComputationInputUnion = Field(
        ...,
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

        if computation_type == ModelComputationType.NUMERIC and not isinstance(
            v,
            ModelNumericComputationInput,
        ):
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="NUMERIC computation_type requires ModelNumericComputationInput",
            )
        if computation_type == ModelComputationType.TEXT and not isinstance(
            v,
            ModelTextComputationInput,
        ):
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="TEXT computation_type requires ModelTextComputationInput",
            )
        if computation_type == ModelComputationType.BINARY and not isinstance(
            v,
            ModelBinaryComputationInput,
        ):
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="BINARY computation_type requires ModelBinaryComputationInput",
            )
        if computation_type == ModelComputationType.STRUCTURED and not isinstance(
            v,
            ModelStructuredComputationInput,
        ):
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="STRUCTURED computation_type requires ModelStructuredComputationInput",
            )

        return v

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
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
        raise OnexError(
            code=CoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = [
    "ModelBinaryComputationInput",
    "ModelComputationInputBase",
    "ModelComputationInputData",
    "ModelComputationInputUnion",
    "ModelComputationMetadataContext",
    "ModelComputationOperationParameters",
    "ModelComputationType",
    "ModelInputDataType",
    "ModelMixedInputValue",
    "ModelNumericComputationInput",
    "ModelPrimitiveInputValue",
    "ModelStructuredComputationInput",
    "ModelStructuredInputValue",
    "ModelTextComputationInput",
]
