"""
YAML parsing utilities for invariant definitions.

This module provides functions for loading invariant sets from YAML files
or strings, with proper error handling using ModelOnexError.

This module is located in utils/ to avoid circular import issues that occur
when importing from models/ due to deep dependency chains.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.enums import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.invariant.model_invariant_set import ModelInvariantSet


def parse_invariant_set_from_yaml(yaml_content: str) -> ModelInvariantSet:
    """
    Parse a YAML string into a ModelInvariantSet.

    Supports two YAML formats for flexibility:

    **Flat format** (fields at root level)::

        name: "My Invariant Set"
        target: "node_example"
        invariants:
          - name: "Latency Check"
            type: latency
            config:
              max_latency_ms: 100

    **Nested format** (wrapped in invariant_set key)::

        invariant_set:
          name: "My Invariant Set"
          target: "node_example"
          invariants:
            - name: "Latency Check"
              type: latency
              config:
                max_latency_ms: 100

    The nested format is automatically unwrapped for consistency. Both formats
    produce identical ModelInvariantSet objects.

    Args:
        yaml_content: YAML string containing invariant set definition.

    Returns:
        ModelInvariantSet parsed from the YAML content.

    Raises:
        ModelOnexError: If YAML is invalid or doesn't match the expected schema.
            Error codes:
            - CONFIGURATION_PARSE_ERROR: Invalid YAML syntax or empty content
            - CONTRACT_VALIDATION_ERROR: Valid YAML but invalid schema
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ModelOnexError(
            message=f"Invalid YAML syntax: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from e

    if data is None:
        raise ModelOnexError(
            message="YAML content is empty or null",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        )

    # Handle nested 'invariant_set' key for flexibility
    if isinstance(data, dict) and "invariant_set" in data:
        data = data["invariant_set"]

    try:
        return ModelInvariantSet.model_validate(data)
    except ValidationError as e:
        raise ModelOnexError(
            message=f"Invalid invariant set schema: {e}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        ) from e


def load_invariant_set_from_file(file_path: Path | str) -> ModelInvariantSet:
    """
    Load a ModelInvariantSet from a YAML file.

    Args:
        file_path: Path to the YAML file containing the invariant set definition.

    Returns:
        ModelInvariantSet parsed from the file.

    Raises:
        ModelOnexError: If file is not found, cannot be read, or contains invalid YAML.
    """
    path = Path(file_path)

    if not path.exists():
        raise ModelOnexError(
            message=f"Invariant set file not found: {path}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ModelOnexError(
            message=f"Failed to read invariant set file: {e}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        ) from e

    return parse_invariant_set_from_yaml(content)


def load_invariant_sets_from_directory(
    directory_path: Path | str,
    patterns: list[str] | None = None,
) -> list[ModelInvariantSet]:
    """Load all ModelInvariantSet definitions from a directory.

    Supports both .yaml and .yml file extensions by default. Files are
    loaded in sorted order by filename.

    Args:
        directory_path: Path to the directory containing YAML files.
        patterns: Glob patterns for matching files. Defaults to
            ["*.yaml", "*.yml"] to support both common YAML extensions.

    Returns:
        List of ModelInvariantSet objects parsed from matching files.

    Raises:
        ModelOnexError: If directory is not found or any file fails to parse.
            Error codes:
            - DIRECTORY_NOT_FOUND: Directory does not exist
            - INVALID_PARAMETER: Path exists but is not a directory
    """
    if patterns is None:
        patterns = ["*.yaml", "*.yml"]

    path = Path(directory_path)

    if not path.exists():
        raise ModelOnexError(
            message=f"Invariant sets directory not found: {path}",
            error_code=EnumCoreErrorCode.DIRECTORY_NOT_FOUND,
        )

    if not path.is_dir():
        raise ModelOnexError(
            message=f"Path is not a directory: {path}",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        )

    # Collect files matching any pattern, avoiding duplicates
    yaml_files: set[Path] = set()
    for pattern in patterns:
        yaml_files.update(path.glob(pattern))

    invariant_sets: list[ModelInvariantSet] = []
    for yaml_file in sorted(yaml_files):
        if yaml_file.is_file():
            invariant_set = load_invariant_set_from_file(yaml_file)
            invariant_sets.append(invariant_set)

    return invariant_sets


__all__ = [
    "load_invariant_set_from_file",
    "load_invariant_sets_from_directory",
    "parse_invariant_set_from_yaml",
]
