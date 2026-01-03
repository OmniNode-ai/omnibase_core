"""
v1.0 Compute subcontract for sequential pipeline transformations.

This module defines the ModelComputeSubcontract model which represents the
complete compute contract for a NodeCompute node. It specifies the transformation
pipeline with abort-on-first-failure semantics, supporting deterministic and
traceable data processing workflows.

The compute subcontract is part of the ONEX contract system and defines:
    - Pipeline identity (name, version, description)
    - Schema references for input/output validation
    - Sequential transformation steps
    - Performance constraints (timeout)

Thread Safety:
    ModelComputeSubcontract is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Pipeline Execution Model:
    Steps are executed sequentially in definition order. If any step fails,
    the pipeline aborts immediately and returns the error. This ensures
    consistent behavior and simplifies error handling.

Example YAML Contract:
    .. code-block:: yaml

        compute_operations:
          version: {major: 1, minor: 0, patch: 0}
          operation_name: "text_normalizer"
          operation_version: {major: 1, minor: 0, patch: 0}
          description: "Normalize text input to uppercase trimmed format"
          input_schema_ref: "schemas/text_input.json"
          output_schema_ref: "schemas/text_output.json"
          pipeline_timeout_ms: 5000
          pipeline:
            - step_name: "trim"
              step_type: "transformation"
              transformation_type: "TRIM"
              transformation_config:
                mode: "BOTH"
            - step_name: "uppercase"
              step_type: "transformation"
              transformation_type: "CASE_CONVERSION"
              transformation_config:
                mode: "UPPER"

Example Python Usage:
    >>> from omnibase_core.models.contracts.subcontracts import ModelComputeSubcontract
    >>> from omnibase_core.models.contracts.subcontracts import ModelComputePipelineStep
    >>> from omnibase_core.enums import EnumComputeStepType, EnumTransformationType
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> contract = ModelComputeSubcontract(
    ...     operation_name="text_normalizer",
    ...     operation_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     description="Normalize text to uppercase",
    ...     pipeline=[...],  # List of ModelComputePipelineStep
    ... )

See Also:
    - omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step: Step definitions
    - omnibase_core.utils.util_compute_executor: Executes these contracts
    - omnibase_core.mixins.mixin_compute_execution: Contract validation utilities
    - docs/architecture/CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md: Full specification
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)


class ModelComputeSubcontract(BaseModel):
    """
    v1.0 Compute subcontract for sequential pipeline transformations.

    Defines transformation pipelines with abort-on-first-failure semantics.
    Steps are executed sequentially in the order defined in the pipeline list.
    If any step fails, the pipeline aborts immediately and returns the error.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it safe
        for concurrent read access from multiple threads or async tasks.

    Contract Versioning:
        The version field tracks the subcontract schema version, not the operation
        version. This allows schema evolution while preserving existing contracts
        for contract parsing.

    Schema References:
        input_schema_ref and output_schema_ref are resolved at contract load time
        (not at execution time). v1.0 logs a warning but does not enforce schema
        validation - this is planned for v1.1.

    Attributes:
        version: Semantic version of the subcontract schema format. Defaults to
            ModelSemVer(major=1, minor=0, patch=0). Used for contract parser compatibility checking.
        operation_name: Unique name identifying this compute operation. Should be
            descriptive and follow naming conventions (e.g., "text_normalizer",
            "user_data_validator").
        operation_version: Semantic version of this operation implementation.
            Allows multiple versions of the same operation to coexist.
        description: Human-readable description of what this operation does.
            Used for documentation and debugging. Defaults to empty string.
        input_schema_ref: Optional reference to a JSON schema for input validation.
            Path or URI to the schema definition. v1.0: resolved but not enforced.
        output_schema_ref: Optional reference to a JSON schema for output validation.
            Path or URI to the schema definition. v1.0: resolved but not enforced.
        pipeline: Ordered list of pipeline steps to execute. Steps run sequentially
            in list order. Each step must have a unique step_name within the pipeline.
        pipeline_timeout_ms: Optional maximum execution time for the entire pipeline
            in milliseconds. Must be > 0 and <= 3600000 (1 hour) if specified.
            v1.0: declared but not enforced.

    Example:
        >>> # Minimal contract with identity transform
        >>> contract = ModelComputeSubcontract(
        ...     operation_name="echo",
        ...     operation_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     pipeline=[
        ...         ModelComputePipelineStep(
        ...             step_name="identity",
        ...             step_type=EnumComputeStepType.TRANSFORMATION,
        ...             transformation_type=EnumTransformationType.IDENTITY,
        ...         ),
        ...     ],
        ... )
    """

    # Identity
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Semantic version of the subcontract schema format",
    )
    operation_name: str
    operation_version: ModelSemVer = Field(
        ...,
        description="Semantic version of this operation implementation",
    )
    description: str = ""

    # Schema references (resolved at load time)
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None

    # Pipeline definition
    pipeline: list[ModelComputePipelineStep]

    # v1.0 Performance (minimal)
    # Upper bound of 3600000ms (1 hour) prevents unreasonable timeout values
    pipeline_timeout_ms: int | None = Field(default=None, gt=0, le=3600000)

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    @field_validator("pipeline")
    @classmethod
    def validate_unique_step_names(
        cls, v: list[ModelComputePipelineStep]
    ) -> list[ModelComputePipelineStep]:
        """Validate that all pipeline step names are unique.

        Each step in the pipeline must have a unique step_name to enable
        unambiguous path references (e.g., $.steps.<step_name>.output).

        Args:
            v: List of pipeline steps to validate.

        Returns:
            The validated list of pipeline steps.

        Raises:
            ValueError: If duplicate step names are found.
        """
        if v:
            step_names = [step.step_name for step in v]
            if len(step_names) != len(set(step_names)):
                # Find duplicates for better error message
                seen: set[str] = set()
                duplicates: list[str] = []
                for name in step_names:
                    if name in seen and name not in duplicates:
                        duplicates.append(name)
                    seen.add(name)
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    f"Pipeline step names must be unique. Duplicates found: {duplicates}"
                )
        return v
