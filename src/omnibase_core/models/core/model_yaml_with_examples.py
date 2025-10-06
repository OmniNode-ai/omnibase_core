from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelYamlWithExamples(BaseModel):
    """Model for YAML files that contain examples sections."""

    model_config = ConfigDict(extra="allow")

    # For schema files with examples
    examples: list[dict[str, Any]] | None = Field(
        default=None, description="Examples section"
    )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelYamlWithExamples":
        """
        Create ModelYamlWithExamples from YAML content.

        This is the only place where yaml.safe_load should be used
        for the ModelYamlWithExamples class.
        """
        try:
            data = yaml.safe_load(yaml_content)
            if data is None:
                data = {}
            if isinstance(data, list):
                # For root-level lists, try to find examples
                return cls(examples=data if data else None)
            return cls(**data)
        except yaml.YAMLError as e:
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid YAML content: {e}",
            ) from e
