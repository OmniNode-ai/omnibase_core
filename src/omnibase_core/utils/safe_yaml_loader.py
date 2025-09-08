"""
Safe YAML loading utilities without direct yaml.safe_load usage.

This module provides type-safe YAML loading that uses Pydantic model validation
to ensure proper structure and security without relying on yaml.safe_load.

Author: ONEX Framework Team
"""

import io
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.model.core.model_generic_yaml import (
    ModelGenericYaml,
    ModelYamlWithExamples,
)


class YamlLoadingError(Exception):
    """Error raised during YAML loading operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


T = TypeVar("T", bound=BaseModel)


# Removed _load_yaml_content function - YAML loading now handled by Pydantic model from_yaml methods


def load_and_validate_yaml_model(path: Path, model_cls: type[T]) -> T:
    """
    Load a YAML file and validate it against the provided Pydantic model class.
    Returns the validated model instance.
    Raises YamlLoadingError if loading or validation fails.

    Args:
        path: Path to the YAML file
        model_cls: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        YamlLoadingError: If file cannot be read, YAML is invalid, or validation fails
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Use the model's from_yaml method if available
        if hasattr(model_cls, "from_yaml"):
            return model_cls.from_yaml(content)

        # Fallback: Use ModelGenericYaml to load, then convert to target model
        generic_model = ModelGenericYaml.from_yaml(content)
        data = generic_model.model_dump()

        # Handle case where YAML root is a list
        if isinstance(data.get("root_list"), list):
            # Try to pass list to model constructor
            return model_cls(data["root_list"])

        # Validate with Pydantic model
        return model_cls(**data)

    except ValidationError as ve:
        raise YamlLoadingError(f"YAML validation error for {path}: {ve}", ve)
    except FileNotFoundError as e:
        raise YamlLoadingError(f"YAML file not found: {path}", e)
    except Exception as e:
        raise YamlLoadingError(f"Failed to load or validate YAML: {path}: {e}", e)


def load_yaml_as_generic(path: Path) -> ModelGenericYaml:
    """
    Load a YAML file using the generic YAML model.

    This is useful for YAML files with unknown or flexible structure.

    Args:
        path: Path to the YAML file

    Returns:
        ModelGenericYaml instance containing the YAML data
    """
    return load_and_validate_yaml_model(path, ModelGenericYaml)


def load_yaml_content_as_model(content: str, model_cls: type[T]) -> T:
    """
    Load YAML content from a string and validate against a Pydantic model.

    Args:
        content: YAML content as string
        model_cls: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        YamlLoadingError: If YAML is invalid or validation fails
    """
    try:
        # Use the model's from_yaml method if available
        if hasattr(model_cls, "from_yaml"):
            return model_cls.from_yaml(content)

        # Fallback: Use ModelGenericYaml to load, then convert to target model
        generic_model = ModelGenericYaml.from_yaml(content)
        data = generic_model.model_dump()

        # Handle case where YAML root is a list
        if isinstance(data.get("root_list"), list):
            return model_cls(data["root_list"])

        return model_cls(**data)

    except ValidationError as ve:
        raise YamlLoadingError(f"YAML validation error: {ve}", ve)
    except Exception as e:
        raise YamlLoadingError(f"Failed to load or validate YAML content: {e}", e)


def _dump_yaml_content(
    data: Any,
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
        yaml_str = yaml.dump(
            data,
            sort_keys=sort_keys,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            explicit_start=explicit_start,
            explicit_end=explicit_end,
            indent=indent,
            width=width,
            **kwargs,
        )
        # Normalize line endings and Unicode characters
        yaml_str = yaml_str.replace("\xa0", " ")
        yaml_str = yaml_str.replace("\r\n", "\n").replace("\r", "\n")
        if "\r" in yaml_str:
            raise YamlLoadingError("Carriage return found in YAML string")

        # Validate UTF-8 encoding
        try:
            yaml_str.encode("utf-8")
        except UnicodeEncodeError as e:
            raise YamlLoadingError(f"Invalid UTF-8 in YAML output: {e}", e)

        return yaml_str
    except yaml.YAMLError as e:
        raise YamlLoadingError(f"YAML serialization error: {e}", e)


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
        YamlLoadingError: If serialization fails
    """
    try:
        # Use to_serializable_dict if available (for compact entrypoint format)
        if hasattr(model, "to_serializable_dict"):
            data = model.to_serializable_dict()
        else:
            data = model.model_dump(mode="json")

        yaml_str = _dump_yaml_content(data, **yaml_options)

        if comment_prefix:
            yaml_str = "\n".join(
                f"{comment_prefix}{line}" if line.strip() else ""
                for line in yaml_str.splitlines()
            )

        return yaml_str
    except Exception as e:
        raise YamlLoadingError(f"Failed to serialize model to YAML: {e}", e)


def serialize_data_to_yaml(
    data: Any,
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
        YamlLoadingError: If serialization fails
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
        raise YamlLoadingError(f"Failed to serialize data to YAML: {e}", e)


def extract_example_from_schema(
    schema_path: Path,
    example_index: int = 0,
) -> dict[str, Any]:
    """
    Extract a node metadata example from a YAML schema file's 'examples' section.
    Returns the example at the given index as a dict.
    Raises OnexError if the schema or example is missing or malformed.

    Args:
        schema_path: Path to the schema YAML file
        example_index: Index of the example to extract (default: 0)

    Returns:
        Dictionary containing the example data

    Raises:
        OnexError: If schema file is invalid or example is not found
    """
    try:
        # Load the schema using Pydantic model
        schema_model = load_and_validate_yaml_model(schema_path, ModelYamlWithExamples)

        # Extract examples
        examples = schema_model.examples
        if not examples:
            raise YamlLoadingError(
                f"No 'examples' section found in schema: {schema_path}",
            )

        if example_index >= len(examples):
            raise YamlLoadingError(
                f"Example index {example_index} out of range for schema: {schema_path}",
            )

        example = examples[example_index]
        if not isinstance(example, dict):
            raise YamlLoadingError(
                f"Example at index {example_index} is not a dict in schema: {schema_path}",
            )

        return example

    except YamlLoadingError:
        raise
    except Exception as e:
        raise YamlLoadingError(
            f"Failed to extract example from schema: {schema_path}: {e}", e
        )
