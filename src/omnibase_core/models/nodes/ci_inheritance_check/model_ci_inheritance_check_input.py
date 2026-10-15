# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the ci-inheritance handler (OMN-17427)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelCiInheritanceCheckInput"]


class ModelCiInheritanceCheckInput(BaseModel):
    """Workflow files on the base and the head of a change, plus the CI host.

    ``organization`` and ``host_repository`` name the one repository every
    other repository inherits its shared CI from (RULING 2026-10-14T20:01:09Z:
    all CI lives in omnibase_core).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    organization: str = Field(min_length=1)
    host_repository: str = Field(min_length=1)
    base_files: list[ModelSourceFile] = Field(default_factory=list)
    head_files: list[ModelSourceFile] = Field(default_factory=list)
