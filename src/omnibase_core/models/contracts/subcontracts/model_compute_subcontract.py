"""
v1.0 Compute subcontract for sequential pipeline transformations.

This module defines the ModelComputeSubcontract model which represents
the complete compute contract for a NodeCompute node. It specifies
the transformation pipeline with abort-on-first-failure semantics.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)


class ModelComputeSubcontract(BaseModel):
    """
    v1.0 Compute subcontract for sequential pipeline transformations.

    Defines transformation pipelines with abort-on-first-failure semantics.
    Steps are executed sequentially in the order defined in the pipeline list.
    If any step fails, the pipeline aborts and returns the error.

    Attributes:
        version: Semantic version of the subcontract schema. Defaults to "1.0.0".
        operation_name: Name of the compute operation.
        operation_version: Version of the compute operation.
        description: Optional description of the compute operation.
        input_schema_ref: Optional reference to input schema (resolved at load time).
        output_schema_ref: Optional reference to output schema (resolved at load time).
        pipeline: List of pipeline steps to execute sequentially.
        pipeline_timeout_ms: Optional timeout for the entire pipeline in milliseconds.
    """

    # Identity
    version: str = "1.0.0"
    operation_name: str
    operation_version: str
    description: str = ""

    # Schema references (resolved at load time)
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None

    # Pipeline definition
    pipeline: list[ModelComputePipelineStep]

    # v1.0 Performance (minimal)
    pipeline_timeout_ms: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid", frozen=True)
