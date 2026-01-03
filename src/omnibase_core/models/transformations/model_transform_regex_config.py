"""
Configuration for regex transformation.

This module defines the configuration model for REGEX transformations
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_regex_flag import EnumRegexFlag


class ModelTransformRegexConfig(BaseModel):
    """
    Configuration for regex transformation.

    Attributes:
        config_type: Discriminator field for union type resolution.
        pattern: The regex pattern to match.
        replacement: The replacement string. Empty string means deletion.
        flags: List of regex flags to apply.
    """

    config_type: Literal["regex"] = "regex"
    pattern: str
    replacement: str = ""
    flags: list[EnumRegexFlag] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
