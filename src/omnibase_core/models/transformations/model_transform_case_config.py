"""
Configuration for case transformation.

This module defines the configuration model for CASE_CONVERSION transformations
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_case_mode import EnumCaseMode


class ModelTransformCaseConfig(BaseModel):
    """
    Configuration for case transformation.

    Attributes:
        config_type: Discriminator field for union type resolution.
        mode: The case transformation mode to apply.
    """

    config_type: Literal["case_conversion"] = "case_conversion"
    mode: EnumCaseMode

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
