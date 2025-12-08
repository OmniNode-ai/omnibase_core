"""
v1.0 Pipeline step types for contract-driven NodeCompute.

This module defines the step types available in v1.0 compute pipelines.
Each step type represents a different category of operation that can be
performed on data flowing through the pipeline.

v1.0 Supported Types:
    VALIDATION:
        Data validation against a schema. v1.0 implements pass-through
        behavior while logging a warning. Full schema validation with
        JSON Schema support is planned for v1.1.

    TRANSFORMATION:
        Applies a pure transformation function to the data. The specific
        transformation is determined by the transformation_type field in
        the step configuration. See EnumTransformationType for available
        transformations.

    MAPPING:
        Constructs a new data structure by combining values from the
        pipeline input and previous step outputs using path expressions.
        Useful for reshaping data or extracting specific fields.

v1.2+ Planned Types:
    CONDITIONAL (deferred): Branch execution based on conditions
    PARALLEL (deferred): Execute multiple transformations concurrently

Thread Safety:
    Enum values are immutable and thread-safe.

Example:
    >>> from omnibase_core.enums import EnumComputeStepType
    >>>
    >>> # Check step type
    >>> if step.step_type == EnumComputeStepType.TRANSFORMATION:
    ...     print(f"Applying {step.transformation_type} transformation")
    >>> elif step.step_type == EnumComputeStepType.MAPPING:
    ...     print(f"Building output with {len(step.mapping_config.field_mappings)} fields")

See Also:
    - omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step: Step model
    - omnibase_core.enums.enum_transformation_type: Transformation types
    - omnibase_core.utils.compute_executor: Uses this enum for step dispatch
"""

from enum import Enum


class EnumComputeStepType(str, Enum):
    """
    v1.0 Pipeline step types for compute pipeline operations.

    Defines the categories of operations available in contract-driven compute
    pipelines. Each step type has specific configuration requirements and
    execution behavior.

    v1.0 includes only the three essential step types. CONDITIONAL and PARALLEL
    step types are planned for v1.2+ to enable branching logic and concurrent
    execution patterns.

    Attributes:
        VALIDATION: Validates input data against a schema reference. In v1.0,
            this is a pass-through operation that logs a warning - full schema
            validation is planned for v1.1. Requires validation_config in the
            step definition.
        TRANSFORMATION: Applies a pure transformation function to the data.
            The specific transformation is specified by the transformation_type
            field (e.g., CASE_CONVERSION, REGEX). Requires transformation_type
            and transformation_config (except for IDENTITY which must have no
            config) in the step definition.
        MAPPING: Constructs a new data structure by resolving path expressions
            to values from the pipeline input or previous step outputs. Useful
            for data reshaping, field extraction, and combining multiple sources.
            Requires mapping_config with field_mappings in the step definition.

    Example:
        >>> # Dispatch logic based on step type
        >>> if step.step_type == EnumComputeStepType.TRANSFORMATION:
        ...     result = execute_transformation(data, step.transformation_type, step.transformation_config)
        >>> elif step.step_type == EnumComputeStepType.MAPPING:
        ...     result = execute_mapping_step(step, input_data, step_results)
        >>> elif step.step_type == EnumComputeStepType.VALIDATION:
        ...     result = execute_validation_step(step, data)
    """

    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    MAPPING = "mapping"
    # v1.2+: CONDITIONAL = "conditional"
    # v1.2+: PARALLEL = "parallel"
