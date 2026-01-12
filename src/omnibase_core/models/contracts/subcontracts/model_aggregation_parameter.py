"""
Aggregation Parameter Model.

Strongly-typed model for aggregation function parameters.
Replaces dict[str, PrimitiveValueType] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_parameter_type import EnumParameterType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelAggregationParameter(BaseModel):
    """
    Strongly-typed aggregation function parameter.

    Replaces loose dict[str, PrimitiveValueType] with validated structure
    ensuring type safety and runtime validation.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

    parameter_name: str = Field(
        ...,
        description="Name of the aggregation parameter",
        min_length=1,
    )

    parameter_value: ModelSchemaValue = Field(
        ...,
        description="Strongly-typed parameter value with schema validation",
    )

    parameter_type: EnumParameterType = Field(
        default=EnumParameterType.AUTO,
        description="Expected type of parameter (auto, string, number, boolean)",
    )

    is_required: bool = Field(
        default=False,
        description="Whether this parameter is required for the aggregation function",
    )

    default_value: ModelSchemaValue | None = Field(
        default=None,
        description="Default value if parameter is not provided",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the parameter purpose",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
