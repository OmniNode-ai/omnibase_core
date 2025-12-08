"""
Transformation models for contract-driven NodeCompute v1.0.

This package provides the configuration models for all transformation types
supported in the v1.0 Contract-Driven NodeCompute specification.

Transformation Config Models:
    - ModelTransformRegexConfig: Configuration for REGEX transformations
    - ModelTransformCaseConfig: Configuration for CASE_CONVERSION transformations
    - ModelTransformTrimConfig: Configuration for TRIM transformations
    - ModelTransformUnicodeConfig: Configuration for NORMALIZE_UNICODE transformations
    - ModelTransformJsonPathConfig: Configuration for JSON_PATH transformations

Step Config Models:
    - ModelMappingConfig: Configuration for MAPPING step type
    - ModelValidationStepConfig: Configuration for VALIDATION step type

Union Types:
    - ModelTransformationConfig: Discriminated union of all transformation configs
"""

from .model_mapping_config import ModelMappingConfig
from .model_transform_case_config import ModelTransformCaseConfig
from .model_transform_json_path_config import ModelTransformJsonPathConfig
from .model_transform_regex_config import ModelTransformRegexConfig
from .model_transform_trim_config import ModelTransformTrimConfig
from .model_transform_unicode_config import ModelTransformUnicodeConfig
from .model_types import ModelTransformationConfig
from .model_validation_step_config import ModelValidationStepConfig

__all__ = [
    "ModelTransformRegexConfig",
    "ModelTransformCaseConfig",
    "ModelTransformTrimConfig",
    "ModelTransformUnicodeConfig",
    "ModelTransformJsonPathConfig",
    "ModelMappingConfig",
    "ModelValidationStepConfig",
    "ModelTransformationConfig",
]
