"""
Discriminated union types for transformation configurations.

This module defines the ModelTransformationConfig union type that uses
Pydantic's discriminated union feature for type-safe transformation config handling.
"""

from typing import Annotated

from pydantic import Field

from .model_transform_case_config import ModelTransformCaseConfig
from .model_transform_json_path_config import ModelTransformJsonPathConfig
from .model_transform_regex_config import ModelTransformRegexConfig
from .model_transform_trim_config import ModelTransformTrimConfig
from .model_transform_unicode_config import ModelTransformUnicodeConfig

# v1.0 Discriminated union - only 5 types (IDENTITY has no config)
ModelTransformationConfig = Annotated[
    ModelTransformRegexConfig
    | ModelTransformCaseConfig
    | ModelTransformTrimConfig
    | ModelTransformUnicodeConfig
    | ModelTransformJsonPathConfig,
    Field(discriminator="config_type"),
]
