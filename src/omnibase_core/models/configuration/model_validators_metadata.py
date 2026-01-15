"""Shared validators for ONEX metadata models.

This module provides reusable validator functions for common metadata fields
shared between ModelOnexMetadata and ModelMetadataBlock.

These validators are designed to be used with Pydantic's @field_validator
decorator pattern:

    from omnibase_core.models.configuration.model_validators_metadata import (
        coerce_to_semver,
        coerce_to_namespace,
        validate_entrypoint_uri,
        validate_identifier_name,
        coerce_protocols_to_list,
    )

    class MyModel(BaseModel):
        @field_validator("version", mode="before")
        @classmethod
        def check_version(cls, v: object) -> ModelSemVer:
            return coerce_to_semver(v, "version")
"""

import ast
import logging
import re

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_node_metadata import Namespace
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)

# Module-level logger for coercion observability
_logger = logging.getLogger(__name__)


def coerce_to_semver(value: object, field_name: str) -> ModelSemVer:
    """Coerce various input types to ModelSemVer.

    This validator handles multiple input formats for semantic version fields:
    - ModelSemVer instances (returned as-is)
    - dict with major/minor/patch keys (converted to ModelSemVer)
    - semver strings like "1.0.0" (parsed using full SemVer 2.0.0 spec)

    Args:
        value: Input value to coerce (ModelSemVer, dict, or str)
        field_name: Name of the field for error messages

    Returns:
        ModelSemVer instance

    Raises:
        ModelOnexError: If value cannot be converted to ModelSemVer
            (error_code: VALIDATION_ERROR)

    Example:
        >>> coerce_to_semver("1.0.0", "version")
        ModelSemVer(major=1, minor=0, patch=0)
        >>> coerce_to_semver({"major": 1, "minor": 2, "patch": 3}, "version")
        ModelSemVer(major=1, minor=2, patch=3)
    """
    if isinstance(value, ModelSemVer):
        _logger.debug(
            "Coercion: field=%s target_type=ModelSemVer original_type=ModelSemVer "
            "-> no coercion needed",
            field_name,
        )
        return value
    if isinstance(value, dict):
        result = ModelSemVer(**value)
        _logger.debug(
            "Coercion: field=%s target_type=ModelSemVer original_type=dict "
            "original_value=%r -> coerced to %s",
            field_name,
            value,
            str(result),
        )
        return result
    if isinstance(value, str):
        result = parse_semver_from_string(value)
        _logger.debug(
            "Coercion: field=%s target_type=ModelSemVer original_type=str "
            "original_value=%r -> coerced to %s",
            field_name,
            value,
            str(result),
        )
        return result
    raise ModelOnexError(
        message=f"{field_name} must be ModelSemVer, dict, or str, got {type(value).__name__}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def coerce_to_namespace(value: object) -> Namespace:
    """Coerce various input types to Namespace.

    This validator handles multiple input formats for namespace fields:
    - Namespace instances (returned as-is)
    - strings (converted to Namespace with value=string)
    - dicts with 'value' key (unpacked to Namespace constructor)

    Args:
        value: Input value to coerce (Namespace, str, or dict)

    Returns:
        Namespace instance

    Raises:
        ModelOnexError: If value cannot be converted to Namespace
            (error_code: VALIDATION_ERROR)

    Example:
        >>> coerce_to_namespace("omnibase.validators")
        Namespace(value="omnibase.validators")
        >>> coerce_to_namespace({"value": "omnibase.validators"})
        Namespace(value="omnibase.validators")
    """
    if isinstance(value, Namespace):
        _logger.debug(
            "Coercion: field=namespace target_type=Namespace original_type=Namespace "
            "-> no coercion needed"
        )
        return value
    if isinstance(value, str):
        result = Namespace(value=value)
        _logger.debug(
            "Coercion: field=namespace target_type=Namespace original_type=str "
            "original_value=%r -> coerced to Namespace",
            value,
        )
        return result
    if isinstance(value, dict) and "value" in value:
        result = Namespace(**value)
        _logger.debug(
            "Coercion: field=namespace target_type=Namespace original_type=dict "
            "original_value=%r -> coerced to Namespace",
            value,
        )
        return result
    raise ModelOnexError(
        message="Namespace must be a Namespace, str, or dict with 'value'",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def validate_entrypoint_uri(value: object) -> str | None:
    """Validate entrypoint is a valid URI string.

    Entrypoints must contain "://" to be valid URI format
    (e.g., "python://file.py", "shell://script.sh").
    Empty strings and None are allowed and normalize to None.

    Args:
        value: Entrypoint URI string or None

    Returns:
        Validated entrypoint string or None

    Raises:
        ModelOnexError: If string is not a valid URI format
            (error_code: VALIDATION_ERROR)

    Example:
        >>> validate_entrypoint_uri("python://my_module.py")
        'python://my_module.py'
        >>> validate_entrypoint_uri(None)
        None
        >>> validate_entrypoint_uri("")
        None
    """
    if value is None or value == "":
        return None
    if isinstance(value, str) and "://" in value:
        return value
    raise ModelOnexError(
        message=f"Entrypoint must be a URI string (e.g., python://file.py), got: {value}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


# Pattern for valid Python identifiers (used for 'name' field validation)
_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_identifier_name(value: str) -> str:
    """Validate name follows Python identifier naming rules.

    Names must start with a letter or underscore, followed by
    letters, numbers, or underscores (Python identifier rules).

    Args:
        value: Name string to validate

    Returns:
        Validated name string (unchanged)

    Raises:
        ModelOnexError: If name contains invalid characters
            (error_code: VALIDATION_ERROR)

    Example:
        >>> validate_identifier_name("my_validator")
        'my_validator'
        >>> validate_identifier_name("_private_tool")
        '_private_tool'
    """
    if not _IDENTIFIER_PATTERN.match(value):
        raise ModelOnexError(
            message=f"Invalid name: {value}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return value


def coerce_protocols_to_list(value: list[str] | str) -> list[str]:
    """Coerce protocols_supported to a list of strings.

    Accepts a list of strings directly, or a string representation
    of a list (parsed via ast.literal_eval for safety).

    Args:
        value: List of protocol strings or string representation

    Returns:
        List of protocol identifier strings

    Raises:
        ModelOnexError: If value cannot be converted to a list
            (error_code: VALIDATION_ERROR)

    Example:
        >>> coerce_protocols_to_list(["validator/v1", "tool/v1"])
        ['validator/v1', 'tool/v1']
        >>> coerce_protocols_to_list("['validator/v1']")
        ['validator/v1']
    """
    original_value = value
    original_type = type(value).__name__
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
            _logger.debug(
                "Coercion: field=protocols_supported target_type=list[str] "
                "original_type=str original_value=%r -> coerced via ast.literal_eval",
                original_value,
            )
        except (ValueError, SyntaxError):
            # ast.literal_eval raises ValueError for malformed expressions
            # and SyntaxError for invalid Python syntax
            raise ModelOnexError(
                message=f"protocols_supported must be a list, got: {value}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
    if not isinstance(value, list):
        raise ModelOnexError(
            message=f"protocols_supported must be a list, got: {value}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    if original_type == "list":
        _logger.debug(
            "Coercion: field=protocols_supported target_type=list[str] "
            "original_type=list -> no coercion needed"
        )
    return value
