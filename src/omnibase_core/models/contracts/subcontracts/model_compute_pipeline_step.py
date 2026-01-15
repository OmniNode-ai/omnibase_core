"""
A single step in the compute pipeline.

This module defines the ModelComputePipelineStep model for v1.0 contract-driven
NodeCompute pipelines. Each step represents a discrete operation in the
sequential transformation pipeline.

Step Types (v1.0):
    VALIDATION:
        Validates data against a schema. v1.0 implements pass-through behavior
        while logging a warning. Full schema validation planned for v1.1.

    TRANSFORMATION:
        Applies a transformation function to the data. Supports multiple
        transformation types: IDENTITY, REGEX, CASE_CONVERSION, TRIM,
        NORMALIZE_UNICODE, and JSON_PATH.

    MAPPING:
        Builds a new data structure by combining values from the pipeline
        input and/or previous step outputs using path expressions.

Thread Safety:
    ModelComputePipelineStep is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Configuration Requirements:
    Each step type requires specific configuration fields:
    - VALIDATION: validation_config (required)
    - TRANSFORMATION: transformation_type (required), transformation_config
      (required for all except IDENTITY, which must NOT have config)
    - MAPPING: mapping_config (required)

Example YAML:
    .. code-block:: yaml

        # Transformation step
        - step_name: "normalize_text"
          step_type: "transformation"
          transformation_type: "case_conversion"
          transformation_config:
            mode: "uppercase"

        # Mapping step
        - step_name: "build_output"
          step_type: "mapping"
          mapping_config:
            field_mappings:
              original_input: "$.input.text"
              normalized: "$.steps.normalize_text.output"

Example Python:
    >>> from omnibase_core.models.contracts.subcontracts import ModelComputePipelineStep
    >>> from omnibase_core.enums import EnumComputeStepType, EnumTransformationType
    >>> from omnibase_core.models.transformations import ModelTransformCaseConfig
    >>> from omnibase_core.enums import EnumCaseMode
    >>>
    >>> step = ModelComputePipelineStep(
    ...     step_name="uppercase",
    ...     step_type=EnumComputeStepType.TRANSFORMATION,
    ...     transformation_type=EnumTransformationType.CASE_CONVERSION,
    ...     transformation_config=ModelTransformCaseConfig(mode=EnumCaseMode.UPPER),
    ... )

See Also:
    - omnibase_core.models.contracts.subcontracts.model_compute_subcontract: Parent contract
    - omnibase_core.utils.util_compute_executor.execute_pipeline_step: Step execution logic
    - omnibase_core.enums.enum_compute_step_type: Step type enumeration
"""

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.models.transformations.model_mapping_config import ModelMappingConfig
from omnibase_core.models.transformations.model_types import ModelTransformationConfig
from omnibase_core.models.transformations.model_validation_step_config import (
    ModelValidationStepConfig,
)


class ModelComputePipelineStep(BaseModel):
    """
    A single step in the compute pipeline.

    Represents one discrete operation in a sequential transformation pipeline.
    v1.0 supports three step types: VALIDATION, TRANSFORMATION, and MAPPING.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it safe
        for concurrent read access from multiple threads or async tasks.

    Step Type Configuration:
        Each step type requires specific configuration fields. The model validator
        enforces these requirements at construction time:

        VALIDATION:
            - validation_config: Required. Specifies schema_ref for validation.

        TRANSFORMATION:
            - transformation_type: Required. Specifies which transformation to apply.
            - transformation_config: Required for all types EXCEPT IDENTITY.
              IDENTITY transformation MUST NOT have a config (enforced).

        MAPPING:
            - mapping_config: Required. Specifies field_mappings with path expressions.

    Path Expression Syntax (for mapping_config):
        - $.input: Full pipeline input
        - $.input.<field>: Input field access
        - $.steps.<step_name>.output: Previous step's output

    Attributes:
        step_name: Unique identifier for this step within the pipeline. Used for
            logging, error messages, and path references in subsequent steps
            (e.g., "$.steps.step_name.output"). Must be unique across all steps.
        step_type: The category of operation this step performs. One of:
            VALIDATION, TRANSFORMATION, or MAPPING.
        transformation_type: For TRANSFORMATION steps only. Specifies which
            transformation function to apply. One of: IDENTITY, REGEX,
            CASE_CONVERSION, TRIM, NORMALIZE_UNICODE, JSON_PATH.
        transformation_config: Configuration for the transformation. Required
            for all transformation types except IDENTITY (which must have None).
            Type depends on transformation_type (e.g., ModelTransformCaseConfig
            for CASE_CONVERSION).
        mapping_config: For MAPPING steps only. Contains field_mappings dict
            that specifies how to build the output structure from path expressions.
        validation_config: For VALIDATION steps only. Contains schema_ref
            for data validation. v1.0: schema not enforced, logs warning.
        enabled: Whether this step should be executed. When False, the step
            is skipped and the previous step's output (or input for first step)
            passes through unchanged. Defaults to True.

    Example:
        >>> # TRANSFORMATION step with configuration
        >>> step = ModelComputePipelineStep(
        ...     step_name="normalize",
        ...     step_type=EnumComputeStepType.TRANSFORMATION,
        ...     transformation_type=EnumTransformationType.CASE_CONVERSION,
        ...     transformation_config=ModelTransformCaseConfig(mode=EnumCaseMode.UPPER),
        ... )
        >>>
        >>> # IDENTITY transformation (no config allowed)
        >>> identity = ModelComputePipelineStep(
        ...     step_name="passthrough",
        ...     step_type=EnumComputeStepType.TRANSFORMATION,
        ...     transformation_type=EnumTransformationType.IDENTITY,
        ... )

    Note:
        Per-step timeout is not supported in v1.0. Use pipeline_timeout_ms on
        the parent ModelComputeSubcontract for overall timeout control.
    """

    step_name: str
    step_type: EnumComputeStepType

    # For transformation steps
    transformation_type: EnumTransformationType | None = None
    transformation_config: ModelTransformationConfig | None = None

    # For mapping steps
    mapping_config: ModelMappingConfig | None = None

    # For validation steps
    validation_config: ModelValidationStepConfig | None = None

    # Common options
    enabled: bool = True
    # v1.0: No per-step timeout - only pipeline-level timeout_ms on contract

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    @model_validator(mode="after")
    def validate_step_config(self) -> "ModelComputePipelineStep":
        """Ensure correct config is provided for step type."""
        if self.step_type == EnumComputeStepType.TRANSFORMATION:
            if self.transformation_type is None:
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    "transformation_type required for transformation steps"
                )
            if (
                self.transformation_config is None
                and self.transformation_type != EnumTransformationType.IDENTITY
            ):
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    "transformation_config required for non-identity transformations"
                )
            # IDENTITY must NOT have config
            if (
                self.transformation_type == EnumTransformationType.IDENTITY
                and self.transformation_config is not None
            ):
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    "transformation_config must be None for IDENTITY transformations"
                )
        if self.step_type == EnumComputeStepType.MAPPING:
            if self.mapping_config is None:
                # error-ok: Pydantic validator requires ValueError
                raise ValueError("mapping_config required for mapping steps")
        if self.step_type == EnumComputeStepType.VALIDATION:
            if self.validation_config is None:
                # error-ok: Pydantic validator requires ValueError
                raise ValueError("validation_config required for validation steps")
        return self
