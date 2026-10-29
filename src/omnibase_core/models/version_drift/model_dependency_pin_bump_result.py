# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The outcome of a dependency pin bump (OMN-21478)."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDependencyPinBumpResult"]


class ModelDependencyPinBumpResult(BaseModel):
    """The rewritten pyproject, or None when the pin already held the tag."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    changed_path: Path | None = None
