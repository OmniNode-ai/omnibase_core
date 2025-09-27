"""
Aggregation Function Model - ONEX Standards Compliant.

Individual model for aggregation function definitions and configurations.
Part of the Aggregation Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelAggregationFunction(BaseModel):
    """
    Aggregation function definition.

    Defines aggregation functions, parameters,
    and computational requirements for data processing.
    """

    function_name: str = Field(
        ...,
        description="Name of the aggregation function",
        min_length=1,
    )

    function_type: str = Field(
        ...,
        description="Type of function (statistical, mathematical, custom)",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable function description",
        min_length=1,
    )

    input_fields: list[str] = Field(
        ...,
        description="Required input fields for function",
        min_length=1,
    )

    output_field: str = Field(
        ...,
        description="Output field name for result",
        min_length=1,
    )

    parameters: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Function-specific parameters",
    )

    null_handling: str = Field(
        default="ignore",
        description="Strategy for handling null values",
    )

    precision_digits: int = Field(
        default=6,
        description="Precision for numeric results",
        ge=1,
        le=15,
    )

    requires_sorting: bool = Field(
        default=False,
        description="Whether function requires sorted input",
    )

    is_associative: bool = Field(
        default=False,
        description="Whether function is associative",
    )

    is_commutative: bool = Field(
        default=False,
        description="Whether function is commutative",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
