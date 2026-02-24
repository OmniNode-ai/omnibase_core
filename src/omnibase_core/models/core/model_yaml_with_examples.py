# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import logging

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

logger = logging.getLogger(__name__)


class ModelYamlWithExamples(BaseModel):
    """Model for YAML files that contain examples sections."""

    model_config = ConfigDict(extra="allow")

    # For schema files with examples
    examples: list[SerializedDict] | None = Field(
        default=None, description="Examples section"
    )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelYamlWithExamples":
        """
        Create ModelYamlWithExamples from YAML content.

        Separates Pydantic ValidationError (expected schema issues) from
        unexpected system errors to improve debugging and error reporting.

        This is the only place where yaml.safe_load should be used
        for the ModelYamlWithExamples class.

        Args:
            yaml_content: YAML string to parse and validate.

        Returns:
            ModelYamlWithExamples: Validated model instance.

        Raises:
            ModelOnexError: With VALIDATION_ERROR code for schema/field
                validation failures (field names and constraints are included
                in the error message for structured debugging).
            ModelOnexError: With CONVERSION_ERROR code for YAML syntax errors.
            ModelOnexError: With INTERNAL_ERROR code for unexpected system
                errors; original exception context is preserved via ``from e``.
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.debug("YAML syntax error in ModelYamlWithExamples.from_yaml: %s", e)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONVERSION_ERROR,
                message=f"Invalid YAML syntax: {e}",
            ) from e

        try:
            if data is None:
                data = {}
            if isinstance(data, list):
                # For root-level lists, try to find examples
                return cls(examples=data if data else None)
            return cls(**data)
        except ValidationError as e:
            # Expected schema validation failure — provide structured field context
            field_errors = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )
            logger.debug(
                "Pydantic validation error in ModelYamlWithExamples.from_yaml — %s",
                field_errors,
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"YAML schema validation failed: {field_errors}",
            ) from e
        except (AttributeError, TypeError, ValueError, RuntimeError) as e:
            # Unexpected system error — re-raise with original context preserved
            logger.debug(
                "Unexpected error in ModelYamlWithExamples.from_yaml: %s",
                e,
                exc_info=True,
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error loading YAML: {e}",
            ) from e
