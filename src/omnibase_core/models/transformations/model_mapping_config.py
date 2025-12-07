"""
v1.0 Mapping configuration for field mapping steps.

This module defines the configuration model for MAPPING step types
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelMappingConfig(BaseModel):
    """
    v1.0 Mapping configuration.

    field_mappings uses simple path expressions:
    - $.input - Access input data
    - $.steps.<name>.output - Access step output

    Attributes:
        config_type: Discriminator field for union type resolution.
        field_mappings: Dictionary mapping output field names to path expressions.
    """

    config_type: Literal["mapping"] = "mapping"
    field_mappings: dict[str, str]

    model_config = ConfigDict(extra="forbid", frozen=True)
