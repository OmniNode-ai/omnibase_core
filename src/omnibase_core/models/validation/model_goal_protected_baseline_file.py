# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalProtectedBaselineFile."""

from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)


class ModelGoalProtectedBaselineFile(BaseModel):
    """One immutable test or fixture file in the protected baseline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: PurePosixPath
    sha256: str

    @field_validator("sha256")
    @classmethod
    def _digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("baseline file digest must use sha256:<64 lowercase hex>")
        return value

    @field_validator("path")
    @classmethod
    def _path_is_repo_relative(cls, value: PurePosixPath) -> PurePosixPath:
        if value.is_absolute() or not value.parts or ".." in value.parts:
            raise ValueError("baseline file path must be repository-relative")
        return value
