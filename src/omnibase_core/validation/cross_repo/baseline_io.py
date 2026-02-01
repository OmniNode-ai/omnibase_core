"""YAML I/O utilities for violation baselines.

Provides read/write functions for baseline files with proper error
handling and format validation.

Related ticket: OMN-1774
"""

from __future__ import annotations

from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_violation_baseline import (
    ModelViolationBaseline,
)


def write_baseline(path: Path, baseline: ModelViolationBaseline) -> None:
    """Write a violation baseline to a YAML file.

    The file format is designed for human readability and version control
    friendliness. Violations are sorted by fingerprint for stable diffs.

    Args:
        path: Path to write the baseline file.
        baseline: The baseline to write.

    Raises:
        ModelOnexError: If the file cannot be written.
    """
    try:
        # Convert to dict for YAML serialization
        data = baseline.model_dump(mode="json")

        # Sort violations by fingerprint for stable output
        data["violations"] = sorted(
            data["violations"],
            key=lambda v: v["fingerprint"],
        )

        # Write with readable formatting
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,  # Preserve field order
                width=120,
            )
    except OSError as e:
        raise ModelOnexError(
            message=f"Failed to write baseline file: {path}",
            error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
            context={"path": str(path), "error": str(e)},
        ) from e


def read_baseline(path: Path) -> ModelViolationBaseline:
    """Read a violation baseline from a YAML file.

    Args:
        path: Path to the baseline file.

    Returns:
        The parsed baseline.

    Raises:
        ModelOnexError: If the file cannot be read or parsed.
    """
    if not path.exists():
        raise ModelOnexError(
            message=f"Baseline file not found: {path}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            context={"path": str(path)},
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            # yaml-ok: Parse raw YAML to dict, then validate through Pydantic below
            data = yaml.safe_load(f)
    except OSError as e:
        raise ModelOnexError(
            message=f"Failed to read baseline file: {path}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            context={"path": str(path), "error": str(e)},
        ) from e
    except yaml.YAMLError as e:
        raise ModelOnexError(
            message=f"Invalid YAML in baseline file: {path}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            context={"path": str(path), "error": str(e)},
        ) from e

    if data is None:
        raise ModelOnexError(
            message=f"Baseline file is empty: {path}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"path": str(path)},
        )

    try:
        return ModelViolationBaseline.model_validate(data)
    except ValueError as e:
        raise ModelOnexError(
            message=f"Invalid baseline format: {path}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            context={"path": str(path), "error": str(e)},
        ) from e


__all__ = ["read_baseline", "write_baseline"]
