"""
A single step in the compute pipeline.

This module defines the ModelComputePipelineStep model for v1.0 contract-driven
NodeCompute pipelines. Each step represents a discrete operation in the
sequential transformation pipeline.
"""

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.models.transformations.model_mapping_config import ModelMappingConfig
from omnibase_core.models.transformations.model_validation_step_config import (
    ModelValidationStepConfig,
)
from omnibase_core.models.transformations.types import ModelTransformationConfig


class ModelComputePipelineStep(BaseModel):
    """
    A single step in the compute pipeline.

    v1.0 supports: VALIDATION, TRANSFORMATION, MAPPING

    Each step type requires its corresponding configuration:
    - VALIDATION requires validation_config
    - TRANSFORMATION requires transformation_type and transformation_config
      (except IDENTITY which must NOT have transformation_config)
    - MAPPING requires mapping_config

    NOTE: No per-step timeout in v1.0. Use pipeline_timeout_ms on contract.

    Attributes:
        step_name: Unique name for this step within the pipeline.
        step_type: The type of step (VALIDATION, TRANSFORMATION, MAPPING).
        transformation_type: For TRANSFORMATION steps, the type of transformation.
        transformation_config: For non-IDENTITY TRANSFORMATION steps, the config.
        mapping_config: For MAPPING steps, the field mapping configuration.
        validation_config: For VALIDATION steps, the validation configuration.
        enabled: Whether this step is enabled. Defaults to True.
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

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_step_config(self) -> "ModelComputePipelineStep":
        """Ensure correct config is provided for step type."""
        if self.step_type == EnumComputeStepType.TRANSFORMATION:
            if self.transformation_type is None:
                raise ValueError("transformation_type required for transformation steps")
            if (
                self.transformation_config is None
                and self.transformation_type != EnumTransformationType.IDENTITY
            ):
                raise ValueError(
                    "transformation_config required for non-identity transformations"
                )
            # IDENTITY must NOT have config
            if (
                self.transformation_type == EnumTransformationType.IDENTITY
                and self.transformation_config is not None
            ):
                raise ValueError(
                    "transformation_config must be None for IDENTITY transformations"
                )
        if self.step_type == EnumComputeStepType.MAPPING:
            if self.mapping_config is None:
                raise ValueError("mapping_config required for mapping steps")
        if self.step_type == EnumComputeStepType.VALIDATION:
            if self.validation_config is None:
                raise ValueError("validation_config required for validation steps")
        return self
