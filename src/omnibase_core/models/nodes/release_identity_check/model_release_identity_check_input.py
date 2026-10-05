# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Immutable facts consumed by the pure release-identity validator."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelReleaseIdentityCheckInput(BaseModel):
    """One tree's declared version, reachable releases and change selection.

    None for changed_files means that exemption cannot be established. An
    empty tuple is a proven empty change set. Collection diagnostics belong to
    the runtime; the handler only evaluates successfully gathered facts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # str(project.version) when the TOML value is truthy, else None: the script
    # compared str(raw) and treated every falsy value as a missing version.
    pyproject_version_raw: str | None = None
    pyproject_version_repr: str | None = None
    pyproject_path: str = "pyproject.toml"
    published_tags: tuple[str, ...] = ()
    changed_files: tuple[str, ...] | None = None
    files: tuple[ModelSourceFile, ...] = ()
    runtime_errors: tuple[str, ...] = ()
    runtime_exit_code: Literal[1, 2] = 1
