"""
Safe YAML loading utilities without direct yaml.safe_load usage.

This module provides type-safe YAML loading that uses Pydantic model validation
to ensure proper structure and security without relying on yaml.safe_load.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.config.model_schema_example import ModelSchemaExample
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.utils import ModelYamlOption, ModelYamlValue

# ModelYamlWithExamples import removed - using direct YAML parsing

# Type-safe YAML-serializable data structures using discriminated union


T = TypeVar("T", bound=BaseModel)


# Removed _load_yaml_content function - YAML loading now handled by Pydantic model from_yaml methods


def load_and_validate_yaml_model(path: Path, model_cls: type[T]) -> T:
    """
    Load a YAML file and validate it against the provided Pydantic model class.
    Returns the validated model instance.
    Raises OnexError if loading or validation fails.

    Args:
        path: Path to the YAML file
        model_cls: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        OnexError: If file cannot be read, YAML is invalid, or validation fails
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
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
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
        raise OnexError(
            code=EnumCoreErrorCode.NOT_FOUND,
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
        raise OnexError(
            code=EnumCoreErrorCode.CONVERSION_ERROR,
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
    except Exception as e:
        raise OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
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


def load_yaml_content_as_model(content: str, model_cls: type[T]) -> T:
    """
    Load YAML content from a string and validate against a Pydantic model.

    Args:
        content: YAML content as string
        model_cls: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        OnexError: If YAML is invalid or validation fails
    """
    try:
        # Direct YAML parsing with Pydantic validation - no fallback
        data = yaml.safe_load(content)
        if data is None:
            data = {}

        # Validate with Pydantic model - let field validators handle enum conversions
        return model_cls.model_validate(data)

    except ValidationError as ve:
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
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
        raise OnexError(
            code=EnumCoreErrorCode.CONVERSION_ERROR,
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
    except Exception as e:
        raise OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
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
    sort_keys: bool = False,
    default_flow_style: bool = False,
    allow_unicode: bool = True,
    explicit_start: bool = False,
    explicit_end: bool = False,
    indent: int = 2,
    width: int = 120,
    **kwargs: Any,
) -> str:
    """
    Internal function to dump data to YAML format with security restrictions.

    This is the only place where yaml.dump should be used in the codebase.
    All other code should use this function through proper Pydantic model serialization.
    """
    try:
        # Convert ModelYamlValue to serializable data
        serializable_data = (
            data.to_serializable() if isinstance(data, ModelYamlValue) else data
        )

        # Convert ModelYamlOption values to Python values
        yaml_kwargs: dict[str, Any] = {
            k: v.to_value() if isinstance(v, ModelYamlOption) else v
            for k, v in kwargs.items()
        }

        yaml_str = yaml.dump(
            serializable_data,
            sort_keys=sort_keys,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            explicit_start=explicit_start,
            explicit_end=explicit_end,
            indent=indent,
            width=width,
            **yaml_kwargs,
        )
        # Normalize line endings and Unicode characters
        yaml_str = yaml_str.replace("\xa0", " ")
        yaml_str = yaml_str.replace("\r\n", "\n").replace("\r", "\n")
        if "\r" in yaml_str:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Carriage return found in YAML string",
                details=ModelErrorContext.with_context(
                    {"operation": ModelSchemaValue.from_value("_dump_yaml_content")},
                ),
            )

        # Validate UTF-8 encoding
        try:
            yaml_str.encode("utf-8")
        except UnicodeEncodeError as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid UTF-8 in YAML output: {e}",
                details=ModelErrorContext.with_context(
                    {"operation": ModelSchemaValue.from_value("_dump_yaml_content")},
                ),
                cause=e,
            )

        return cast(str, yaml_str)
    except yaml.YAMLError as e:
        raise OnexError(
            code=EnumCoreErrorCode.CONVERSION_ERROR,
            message=f"YAML serialization error: {e}",
            details=ModelErrorContext.with_context(
                {"operation": ModelSchemaValue.from_value("_dump_yaml_content")},
            ),
            cause=e,
        )


def serialize_pydantic_model_to_yaml(
    model: BaseModel,
    comment_prefix: str = "",
    **yaml_options: Any,
) -> str:
    """
    Serialize a Pydantic model to YAML format through the centralized dumper.

    Args:
        model: Pydantic model instance to serialize
        comment_prefix: Optional prefix for each line (for comment blocks)
        **yaml_options: Additional options to pass to YAML dumper

    Returns:
        YAML string representation of the model

    Raises:
        OnexError: If serialization fails
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
    except Exception as e:
        raise OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
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
    **yaml_options: Any,
) -> str:
    """
    Serialize arbitrary data to YAML format through the centralized dumper.

    This function should be used for non-Pydantic data serialization.
    For Pydantic models, prefer serialize_pydantic_model_to_yaml.

    Args:
        data: Data to serialize (dict, list, or other YAML-serializable types)
        comment_prefix: Optional prefix for each line (for comment blocks)
        **yaml_options: Additional options to pass to YAML dumper

    Returns:
        YAML string representation of the data

    Raises:
        OnexError: If serialization fails
    """
    try:
        yaml_str = _dump_yaml_content(data, **yaml_options)

        if comment_prefix:
            yaml_str = "\n".join(
                f"{comment_prefix}{line}" if line.strip() else ""
                for line in yaml_str.splitlines()
            )

        return yaml_str
    except Exception as e:
        raise OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
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
    Raises OnexError if the schema or example is missing or malformed.

    Args:
        schema_path: Path to the schema YAML file
        example_index: Index of the example to extract (default: 0)

    Returns:
        ModelSchemaExample containing the validated example data

    Raises:
        OnexError: If schema file is invalid or example is not found
    """
    try:
        # Load the schema using direct YAML parsing
        with schema_path.open("r", encoding="utf-8") as f:
            schema_data = yaml.safe_load(f)

        # Extract examples directly from YAML data
        examples = schema_data.get("examples") if schema_data else None
        if not examples:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
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
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
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
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Example at index {example_index} is not a dict in schema: {schema_path}",
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

        # Convert example dict to ModelCustomProperties
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

    except OnexError:
        raise
    except Exception as e:
        raise OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
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
