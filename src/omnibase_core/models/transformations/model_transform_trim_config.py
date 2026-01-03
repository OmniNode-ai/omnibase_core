"""
Configuration for whitespace trimming.

This module defines the configuration model for TRIM transformations
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_trim_mode import EnumTrimMode


class ModelTransformTrimConfig(BaseModel):
    """
    Configuration for whitespace trimming.

    Attributes:
        config_type: Discriminator field for union type resolution.
        mode: The trim mode to apply. Defaults to BOTH.
    """

    config_type: Literal["trim"] = "trim"
    mode: EnumTrimMode = EnumTrimMode.BOTH

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
