"""
Configuration for JSONPath extraction.

This module defines the configuration model for JSON_PATH transformations
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class ModelTransformJsonPathConfig(BaseModel):
    """
    Configuration for JSONPath extraction.

    Attributes:
        config_type: Discriminator field for union type resolution.
        path: The JSONPath expression to extract data (must start with "$").
    """

    config_type: Literal["json_path"] = "json_path"
    path: str

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that path is non-empty and starts with '$'."""
        if not v or not v.strip():
            # error-ok: Pydantic validator requires ValueError
            raise ValueError("path cannot be empty")
        if not v.startswith("$"):
            # error-ok: Pydantic validator requires ValueError
            raise ValueError("path must start with '$'")
        return v
