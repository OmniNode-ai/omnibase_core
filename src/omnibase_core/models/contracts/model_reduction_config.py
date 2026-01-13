"""
Reduction Configuration Model.

Data reduction operation specifications for NodeReducer implementations.
Defines reduction algorithms, aggregation functions, and data processing patterns
for efficient data consolidation.

Part of the "one model per file" convention for clean architecture.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelReductionConfig(BaseModel):
    """
    Data reduction operation specifications.

    Defines reduction algorithms, aggregation functions,
    and data processing patterns for efficient data consolidation.
    """

    operation_type: str = Field(
        default=...,
        description="Type of reduction operation (fold, accumulate, merge, aggregate, etc.)",
        min_length=1,
    )

    reduction_function: str = Field(
        default=...,
        description="Reduction function identifier",
        min_length=1,
    )

    associative: bool = Field(
        default=True,
        description="Whether the reduction operation is associative",
    )

    commutative: bool = Field(
        default=False,
        description="Whether the reduction operation is commutative",
    )

    identity_element: str | None = Field(
        default=None,
        description="Identity element for the reduction operation",
    )

    chunk_size: int = Field(
        default=1000,
        description="Chunk size for batch reduction operations",
        ge=1,
    )

    parallel_enabled: bool = Field(
        default=True,
        description="Enable parallel reduction processing",
    )

    intermediate_results_caching: bool = Field(
        default=True,
        description="Cache intermediate reduction results",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
