"""
Safe YAML loading utilities using yaml.safe_load plus Pydantic validation.

This module provides type-safe YAML loading that uses yaml.safe_load for parsing
combined with Pydantic model validation to ensure proper structure and security.

Security:
    This module uses yaml.safe_load() exclusively for all YAML parsing operations.
    This is a critical security measure that prevents arbitrary code execution
    through malicious YAML files.

    - yaml.safe_load() only parses standard YAML types (strings, numbers, lists, dicts)
    - yaml.load() with Loader=yaml.Loader would allow arbitrary Python object
      instantiation via YAML tags like !!python/object, which could execute
      malicious code during deserialization
    - Pydantic validation provides an additional layer of type safety after parsing

    Trust Model:
        - YAML file content is treated as UNTRUSTED input
        - yaml.safe_load() ensures no code execution during parsing
        - Pydantic validates structure against expected schemas
        - File paths should still be validated to prevent path traversal attacks

    Defense in Depth:
        1. yaml.safe_load() - prevents arbitrary Python object construction
        2. Pydantic validation - ensures expected structure and types
        3. ModelOnexError wrapping - provides structured error handling

    See Also:
        - UtilContractLoader._validate_yaml_content_security() for additional
          YAML content security checks (size limits, suspicious patterns)
        - https://pyyaml.org/wiki/PyYAMLDocumentation#loading-yaml

.. versionadded:: 0.3.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Unpack

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.examples.model_schema_example import ModelSchemaExample
from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
from omnibase_core.types.typed_dict_yaml_dump_options import TypedDictYamlDumpOptions

# ModelYamlWithExamples import removed - using direct YAML parsing

# Type-safe YAML-serializable data structures using discriminated union


# Removed _load_yaml_content function - YAML loading now handled by Pydantic model from_yaml methods


def load_and_validate_yaml_model[T: BaseModel](path: Path, model_cls: type[T]) -> T:
    """
    Load a YAML file and validate it against the provided Pydantic model class.
    Returns the validated model instance.
    Raises ModelOnexError if loading or validation fails.

    Args:
        path: Path to the YAML file
        model_cls: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        ModelOnexError: If file cannot be read, YAML is invalid, or validation fails
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Direct YAML parsing with Pydantic validation - no fallback
        data = yaml.safe_load(content)
        if data is None:
            data = {}

        # Validate with Pydantic model - let field validators handle enum conversions
        return model_cls.model_validate(data)

    except ValidationError as ve:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"YAML validation error for {path}: {ve}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_and_validate_yaml_model",
                    ),
                    "path": ModelSchemaValue.from_value(str(path)),
                },
            ),
            cause=ve,
        )
    except FileNotFoundError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.NOT_FOUND,
            message=f"YAML file not found: {path}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_and_validate_yaml_model",
                    ),
                    "path": ModelSchemaValue.from_value(str(path)),
                },
            ),
            cause=e,
        )
    except yaml.YAMLError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            message=f"YAML parsing error for {path}: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_and_validate_yaml_model",
                    ),
                    "path": ModelSchemaValue.from_value(str(path)),
                },
            ),
            cause=e,
        )
    except (AttributeError, OSError, RuntimeError, TypeError) as e:
        # Catch I/O errors, Pydantic validation runtime errors, and model attribute errors
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=f"Failed to load or validate YAML: {path}: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_and_validate_yaml_model",
                    ),
                    "path": ModelSchemaValue.from_value(str(path)),
                },
            ),
            cause=e,
        )


# load_yaml_as_generic function removed - ModelGenericYaml anti-pattern eliminated


def load_yaml_content_as_model[T: BaseModel](content: str, model_cls: type[T]) -> T:
    """
    Load YAML content from a string and validate against a Pydantic model.

    Args:
        content: YAML content as string
        model_cls: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        ModelOnexError: If YAML is invalid or validation fails
    """
    try:
        # Direct YAML parsing with Pydantic validation - no fallback
        data = yaml.safe_load(content)
        if data is None:
            data = {}

        # Validate with Pydantic model - let field validators handle enum conversions
        return model_cls.model_validate(data)

    except ValidationError as ve:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"YAML validation error: {ve}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_yaml_content_as_model",
                    ),
                },
            ),
            cause=ve,
        )
    except yaml.YAMLError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            message=f"YAML parsing error: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_yaml_content_as_model",
                    ),
                },
            ),
            cause=e,
        )
    except (AttributeError, RuntimeError, TypeError, ValueError) as e:
        # Catch Pydantic validation runtime errors or type conversion errors
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=f"Failed to load or validate YAML content: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "load_yaml_content_as_model",
                    ),
                },
            ),
            cause=e,
        )


def _dump_yaml_content(
    data: object,
    **kwargs: Unpack[TypedDictYamlDumpOptions],
) -> str:
    """
    Internal function to dump data to YAML format with security restrictions.

    This is the only place where yaml.dump should be used in the codebase.
    All other code should use this function through proper Pydantic model serialization.

    Args:
        data: Data to serialize to YAML
        **kwargs: Type-safe YAML dump options (see TypedDictYamlDumpOptions)

    Returns:
        YAML string representation of the data
    """
    try:
        # Convert ModelYamlValue to serializable data
        serializable_data = (
            data.to_serializable() if isinstance(data, ModelYamlValue) else data
        )

        # Extract options with defaults
        sort_keys = kwargs.get("sort_keys", False)
        default_flow_style = kwargs.get("default_flow_style", False)
        allow_unicode = kwargs.get("allow_unicode", True)
        explicit_start = kwargs.get("explicit_start", False)
        explicit_end = kwargs.get("explicit_end", False)
        indent = kwargs.get("indent", 2)
        width = kwargs.get("width", 120)

        # Call yaml.dump with explicit parameters for type safety
        yaml_str: str = yaml.dump(
            serializable_data,
            sort_keys=sort_keys,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            explicit_start=explicit_start,
            explicit_end=explicit_end,
            indent=indent,
            width=width,
        )
        # Normalize line endings and Unicode characters
        yaml_str = yaml_str.replace("\xa0", " ")
        yaml_str = yaml_str.replace("\r\n", "\n").replace("\r", "\n")
        if "\r" in yaml_str:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Carriage return found in YAML string",
                details=ModelErrorContext.with_context(
                    {"operation": ModelSchemaValue.from_value("_dump_yaml_content")},
                ),
            )

        # Validate UTF-8 encoding
        try:
            yaml_str.encode("utf-8")
        except UnicodeEncodeError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid UTF-8 in YAML output: {e}",
                details=ModelErrorContext.with_context(
                    {"operation": ModelSchemaValue.from_value("_dump_yaml_content")},
                ),
                cause=e,
            )

        return yaml_str
    except yaml.YAMLError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            message=f"YAML serialization error: {e}",
            details=ModelErrorContext.with_context(
                {"operation": ModelSchemaValue.from_value("_dump_yaml_content")},
            ),
            cause=e,
        )


def serialize_pydantic_model_to_yaml(
    model: BaseModel,
    comment_prefix: str = "",
    **yaml_options: Unpack[TypedDictYamlDumpOptions],
) -> str:
    """
    Serialize a Pydantic model to YAML format through the centralized dumper.

    Args:
        model: Pydantic model instance to serialize
        comment_prefix: Optional prefix for each line (for comment blocks)
        **yaml_options: Type-safe YAML dump options (see TypedDictYamlDumpOptions)

    Returns:
        YAML string representation of the model

    Raises:
        ModelOnexError: If serialization fails
    """
    try:
        # Use to_serializable_dict if available (for compact entrypoint format)
        if hasattr(model, "to_serializable_dict"):
            data = model.to_serializable_dict()
        else:
            data = model.model_dump(mode="json")

        # Convert to ModelYamlValue for type-safe dumping
        yaml_data = ModelYamlValue.from_schema_value(ModelSchemaValue.from_value(data))
        yaml_str = _dump_yaml_content(yaml_data, **yaml_options)

        if comment_prefix:
            yaml_str = "\n".join(
                f"{comment_prefix}{line}" if line.strip() else ""
                for line in yaml_str.splitlines()
            )

        return yaml_str
    except (AttributeError, RuntimeError, TypeError, yaml.YAMLError) as e:
        # Catch runtime errors, model attribute errors, type conversion errors, or YAML serialization errors
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=f"Failed to serialize model to YAML: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "serialize_pydantic_model_to_yaml",
                    ),
                },
            ),
            cause=e,
        )


def serialize_data_to_yaml(
    data: object,
    comment_prefix: str = "",
    **yaml_options: Unpack[TypedDictYamlDumpOptions],
) -> str:
    """
    Serialize arbitrary data to YAML format through the centralized dumper.

    This function should be used for non-Pydantic data serialization.
    For Pydantic models, prefer serialize_pydantic_model_to_yaml.

    Args:
        data: Data to serialize (dict, list, or other YAML-serializable types)
        comment_prefix: Optional prefix for each line (for comment blocks)
        **yaml_options: Type-safe YAML dump options (see TypedDictYamlDumpOptions)

    Returns:
        YAML string representation of the data

    Raises:
        ModelOnexError: If serialization fails
    """
    try:
        yaml_str = _dump_yaml_content(data, **yaml_options)

        if comment_prefix:
            yaml_str = "\n".join(
                f"{comment_prefix}{line}" if line.strip() else ""
                for line in yaml_str.splitlines()
            )

        return yaml_str
    except (AttributeError, RuntimeError, TypeError, yaml.YAMLError) as e:
        # Catch runtime errors, attribute errors, type conversion errors, or YAML serialization errors
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=f"Failed to serialize data to YAML: {e}",
            details=ModelErrorContext.with_context(
                {"operation": ModelSchemaValue.from_value("serialize_data_to_yaml")},
            ),
            cause=e,
        )


def extract_example_from_schema(
    schema_path: Path,
    example_index: int = 0,
) -> ModelSchemaExample:
    """
    Extract a node metadata example from a YAML schema file's 'examples' section.
    Returns the example at the given index as a typed model.
    Raises ModelOnexError if the schema or example is missing or malformed.

    Args:
        schema_path: Path to the schema YAML file
        example_index: Index of the example to extract (default: 0)

    Returns:
        ModelSchemaExample containing the validated example data

    Raises:
        ModelOnexError: If schema file is invalid or example is not found
    """
    try:
        # Load the schema using direct YAML parsing
        with schema_path.open("r", encoding="utf-8") as f:
            schema_data = yaml.safe_load(f)

        # Extract examples directly from YAML data
        examples = schema_data.get("examples") if schema_data else None
        if not examples:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"No 'examples' section found in schema: {schema_path}",
                details=ModelErrorContext.with_context(
                    {
                        "operation": ModelSchemaValue.from_value(
                            "extract_example_from_schema",
                        ),
                        "path": ModelSchemaValue.from_value(str(schema_path)),
                        "example_index": ModelSchemaValue.from_value(example_index),
                    },
                ),
            )

        if example_index >= len(examples):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Example index {example_index} out of range for schema: {schema_path}",
                details=ModelErrorContext.with_context(
                    {
                        "operation": ModelSchemaValue.from_value(
                            "extract_example_from_schema",
                        ),
                        "path": ModelSchemaValue.from_value(str(schema_path)),
                        "example_index": ModelSchemaValue.from_value(example_index),
                        "examples_count": ModelSchemaValue.from_value(len(examples)),
                    },
                ),
            )

        example = examples[example_index]
        if not isinstance(example, dict):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Example at index {example_index} is not a dict[str, Any] in schema: {schema_path}",
                details=ModelErrorContext.with_context(
                    {
                        "operation": ModelSchemaValue.from_value(
                            "extract_example_from_schema",
                        ),
                        "path": ModelSchemaValue.from_value(str(schema_path)),
                        "example_index": ModelSchemaValue.from_value(example_index),
                        "example_type": ModelSchemaValue.from_value(
                            type(example).__name__,
                        ),
                    },
                ),
            )

        # Convert example dict[str, Any] to ModelCustomProperties
        custom_props = ModelCustomProperties()
        if isinstance(example, dict):
            for key, value in example.items():
                if isinstance(value, str):
                    custom_props.set_custom_string(key, value)
                elif isinstance(value, (int, float)):
                    custom_props.set_custom_number(key, float(value))
                elif isinstance(value, bool):
                    custom_props.set_custom_flag(key, value)

        # Return typed model instead of dict[str, Any]
        return ModelSchemaExample(
            example_data=custom_props,
            example_index=example_index,
            schema_path=str(schema_path),
            schema_version=None,  # Set to None as default since we don't extract version info
            is_validated=True,
        )

    except ModelOnexError:
        raise
    except FileNotFoundError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.NOT_FOUND,
            message=f"Schema file not found: {schema_path}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "extract_example_from_schema",
                    ),
                    "path": ModelSchemaValue.from_value(str(schema_path)),
                    "example_index": ModelSchemaValue.from_value(example_index),
                },
            ),
            cause=e,
        )
    except yaml.YAMLError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            message=f"YAML parsing error in schema file: {schema_path}: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "extract_example_from_schema",
                    ),
                    "path": ModelSchemaValue.from_value(str(schema_path)),
                    "example_index": ModelSchemaValue.from_value(example_index),
                },
            ),
            cause=e,
        )
    except PYDANTIC_MODEL_ERRORS as e:
        # Catch dict access errors, type conversion errors, or data structure issues
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=f"Failed to extract example from schema: {schema_path}: {e}",
            details=ModelErrorContext.with_context(
                {
                    "operation": ModelSchemaValue.from_value(
                        "extract_example_from_schema",
                    ),
                    "path": ModelSchemaValue.from_value(str(schema_path)),
                    "example_index": ModelSchemaValue.from_value(example_index),
                },
            ),
            cause=e,
        )
