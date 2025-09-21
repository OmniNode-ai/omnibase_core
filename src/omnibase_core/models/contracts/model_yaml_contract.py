"""
YAML Contract Model

Pydantic model for validating YAML contract files following ONEX standards.
Replaces manual YAML validation with proper type-safe validation.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from ...enums.enum_node_type import EnumNodeType
from ..metadata.model_semver import ModelSemVer


class ModelYamlContract(BaseModel):
    """
    YAML contract model with Pydantic validation.

    Provides automatic validation of contract_version and node_type fields
    that were previously validated manually in scripts.
    """

    contract_version: ModelSemVer = Field(
        description="Contract version using semantic versioning"
    )
    node_type: EnumNodeType = Field(description="ONEX node type classification")

    # Optional fields that may appear in contract files
    description: Optional[str] = Field(
        default=None, description="Optional contract description"
    )

    # Allow additional fields for flexibility
    model_config = {"extra": "allow"}

    @classmethod
    def validate_yaml_content(
        cls,
        yaml_data: dict[
            str, str | int | float | bool | None | list[str] | dict[str, str]
        ],
    ) -> ModelYamlContract:
        """
        Validate YAML content using Pydantic model validation.

        Args:
            yaml_data: Parsed YAML content as dictionary

        Returns:
            Validated ModelYamlContract instance

        Raises:
            ValidationError: If contract doesn't meet requirements
        """
        return cls.model_validate(yaml_data)
