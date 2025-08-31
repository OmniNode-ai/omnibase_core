# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.282097'
# description: Stamped by ToolPython
# entrypoint: python://yaml_extractor
# hash: 420b7eb2a10b9f24804b76f860cbeef6013b92027bd5730fd8eed836fd8a1570
# last_modified_at: '2025-05-29T14:14:01.004280+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: yaml_extractor.py
# namespace: python://omnibase.utils.yaml_extractor
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 61b925ef-aa72-4f23-8cc0-77681c4c69f0
# version: 1.0.0
# === /OmniNode:Metadata ===


from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


def extract_example_from_schema(
    schema_path: Path,
    example_index: int = 0,
) -> dict[str, Any]:
    """
    Extract a node metadata example from a YAML schema file's 'examples' section.
    Returns the example at the given index as a dict.
    Raises OmniBaseError if the schema or example is missing or malformed.
    """
    try:
        with schema_path.open("r") as f:
            data = yaml.safe_load(f)
        examples = data.get("examples")
        if not examples or not isinstance(examples, list):
            raise OnexError(
                CoreErrorCode.MISSING_REQUIRED_PARAMETER,
                f"No 'examples' section found in schema: {schema_path}",
            )
        if example_index >= len(examples):
            raise OnexError(
                CoreErrorCode.MISSING_REQUIRED_PARAMETER,
                f"Example index {example_index} out of range for schema: {schema_path}",
            )
        example = examples[example_index]
        if not isinstance(example, dict):
            raise OnexError(
                CoreErrorCode.SCHEMA_VALIDATION_FAILED,
                f"Example at index {example_index} is not a dict in schema: {schema_path}",
            )
        return example
    except Exception as e:
        raise OnexError(
            CoreErrorCode.SCHEMA_VALIDATION_FAILED,
            f"Failed to extract example from schema: {schema_path}: {e}",
        )


def load_and_validate_yaml_model(path: Path, model_cls: type[BaseModel]) -> BaseModel:
    """
    Load a YAML file and validate it against the provided Pydantic model class.
    Returns the validated model instance.
    Raises OmniBaseError if loading or validation fails.
    """
    try:
        with path.open("r") as f:
            data = yaml.safe_load(f)
        return model_cls(**data)
    except ValidationError as ve:
        raise OnexError(
            CoreErrorCode.SCHEMA_VALIDATION_FAILED,
            f"YAML validation error for {path}: {ve}",
        )
    except Exception as e:
        raise OnexError(
            CoreErrorCode.SCHEMA_VALIDATION_FAILED,
            f"Failed to load or validate YAML: {path}: {e}",
        )


# TODO: Add CLI and formatting utilities for M1+
