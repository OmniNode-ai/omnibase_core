# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure YAML loading helpers for OmniGate repository configuration."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import NoReturn

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gate import ModelOmniGateConfig

DEFAULT_OMNIGATE_CONFIG_NAMES: tuple[str, ...] = (
    ".omnigate.yaml",
    ".omnigate.yml",
)


def _validate_candidate_name(candidate_name: str) -> None:
    candidate_path = Path(candidate_name)
    if (
        not candidate_name
        or candidate_path.is_absolute()
        or candidate_path.name != candidate_name
    ):
        raise ModelOnexError(
            "OmniGate config candidate names must be relative file names",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            candidate_name=candidate_name,
        )


def _raise_config_parse_error(message: str, config_path: Path | None) -> NoReturn:
    if config_path is None:
        raise ModelOnexError(
            message,
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        )
    raise ModelOnexError(
        message,
        error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        file_path=str(config_path),
    )


def discover_omnigate_config(
    repo_path: Path,
    *,
    candidate_names: Iterable[str] = DEFAULT_OMNIGATE_CONFIG_NAMES,
) -> Path | None:
    """Return the first OmniGate config file found under ``repo_path``."""
    if not repo_path.exists():
        raise ModelOnexError(
            "OmniGate config discovery root does not exist",
            error_code=EnumCoreErrorCode.DIRECTORY_NOT_FOUND,
            file_path=str(repo_path),
        )
    if not repo_path.is_dir():
        raise ModelOnexError(
            "OmniGate config discovery root must be a directory",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            file_path=str(repo_path),
        )

    for candidate_name in candidate_names:
        _validate_candidate_name(candidate_name)
        candidate_path = repo_path / candidate_name
        if candidate_path.is_file():
            return candidate_path

    return None


def from_yaml_omnigate_config(
    content: str,
    *,
    config_path: Path | None = None,
) -> ModelOmniGateConfig:
    """Parse YAML content into a validated OmniGate config model."""
    try:
        raw = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        _raise_config_parse_error(
            f"OmniGate config YAML is invalid: {exc}",
            config_path,
        )
    if raw is None:
        _raise_config_parse_error(
            "OmniGate config YAML must not be empty",
            config_path,
        )
    if not isinstance(raw, Mapping):
        _raise_config_parse_error(
            "OmniGate config YAML must contain a mapping at the document root",
            config_path,
        )

    return ModelOmniGateConfig.model_validate(dict(raw))


def load_omnigate_config(config_path: Path) -> ModelOmniGateConfig:
    """Load and validate a maintainer-authored OmniGate YAML config file."""
    if not config_path.is_file():
        raise ModelOnexError(
            "OmniGate config file does not exist",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            file_path=str(config_path),
        )

    return from_yaml_omnigate_config(
        config_path.read_text(encoding="utf-8"),
        config_path=config_path,
    )


__all__ = [
    "DEFAULT_OMNIGATE_CONFIG_NAMES",
    "discover_omnigate_config",
    "load_omnigate_config",
]
