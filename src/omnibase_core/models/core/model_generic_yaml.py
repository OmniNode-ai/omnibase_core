# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Generic YAML models for common YAML structure patterns.

These models provide type-safe validation for various YAML structures
that appear throughout the codebase, ensuring proper validation without
relying on yaml.safe_load() directly.

"""

import logging
from typing import TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Import extracted YAML model classes
from omnibase_core.models.core.model_yaml_configuration import ModelYamlConfiguration
from omnibase_core.models.core.model_yaml_dictionary import ModelYamlDictionary
from omnibase_core.models.core.model_yaml_list import ModelYamlList
from omnibase_core.models.core.model_yaml_metadata import ModelYamlMetadata
from omnibase_core.models.core.model_yaml_policy import ModelYamlPolicy
from omnibase_core.models.core.model_yaml_registry import ModelYamlRegistry
from omnibase_core.models.core.model_yaml_state import ModelYamlState
from omnibase_core.models.core.model_yaml_with_examples import ModelYamlWithExamples
from omnibase_core.models.errors.model_onex_error import ModelOnexError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelGenericYaml(BaseModel):
    """Generic YAML model for unstructured YAML data."""

    model_config = ConfigDict(extra="allow")

    # Allow any additional fields for maximum flexibility
    root_list: list[object] | None = Field(
        default=None, description="Root level list for YAML arrays"
    )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelGenericYaml":
        """
        Create ModelGenericYaml from YAML content.

        Separates Pydantic ValidationError (expected schema issues) from
        unexpected system errors to improve debugging and error reporting.

        This is the only place where yaml.safe_load should be used
        for the ModelGenericYaml class.

        Args:
            yaml_content: YAML string to parse and validate.

        Returns:
            ModelGenericYaml: Validated model instance.

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
            logger.debug("YAML syntax error in ModelGenericYaml.from_yaml: %s", e)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONVERSION_ERROR,
                message=f"Invalid YAML syntax: {e}",
            ) from e

        try:
            if data is None:
                data = {}
            if isinstance(data, list):
                # For root-level lists, wrap in a dict
                return cls(root_list=data)
            return cls(**data)
        except ValidationError as e:
            # Expected schema validation failure — provide structured field context
            field_errors = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )
            logger.debug(
                "Pydantic validation error in ModelGenericYaml.from_yaml — %s",
                field_errors,
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"YAML schema validation failed: {field_errors}",
            ) from e
        except (AttributeError, TypeError, ValueError, RuntimeError) as e:
            # Unexpected system error — re-raise with original context preserved
            logger.debug(
                "Unexpected error in ModelGenericYaml.from_yaml: %s",
                e,
                exc_info=True,
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error loading YAML: {e}",
            ) from e


# Public API exports
__all__ = [
    "ModelGenericYaml",
    "ModelYamlConfiguration",
    "ModelYamlDictionary",
    "ModelYamlList",
    "ModelYamlMetadata",
    "ModelYamlPolicy",
    "ModelYamlRegistry",
    "ModelYamlState",
    "ModelYamlWithExamples",
]
