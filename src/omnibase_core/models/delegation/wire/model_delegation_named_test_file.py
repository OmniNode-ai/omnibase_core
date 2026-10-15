# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One test file a delegation request carries (OMN-17427)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_NAMED_TEST_FILE_CHARS = 200_000


def inside_workspace(relative: str) -> bool:
    """Whether a workspace-relative path stays inside the sandbox."""
    path = PurePosixPath(relative)
    return not (path.is_absolute() or ".." in path.parts or ".git" in path.parts)


class ModelDelegationNamedTestFile(BaseModel):
    """One test file a request carries: where it goes in the sandbox, and its source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(..., min_length=1, description="Workspace-relative path.")
    content: str = Field(..., max_length=MAX_NAMED_TEST_FILE_CHARS)

    @model_validator(mode="after")
    def _validate_path(self) -> Self:
        if not inside_workspace(self.path):
            raise ValueError(f"test file {self.path!r} must stay inside the workspace")
        return self


__all__: list[str] = [
    "MAX_NAMED_TEST_FILE_CHARS",
    "ModelDelegationNamedTestFile",
    "inside_workspace",
]
