# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for the source_file_gather EFFECT node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.source_file_gather.model_gathered_source_file import (
    ModelGatheredSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_skipped_source_file import (
    ModelSkippedSourceFile,
)

__all__ = ["ModelSourceFileGatherOutput"]


class ModelSourceFileGatherOutput(BaseModel):
    """Result of a source_file_gather run.

    Attributes:
        root: The directory that was scanned (echoed from the request).
        files: Eligible files, each carrying its content.
        skipped: Files considered but excluded, with a skip reason.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-path-ok: directory that was scanned, not a UUID
    root: str
    files: list[ModelGatheredSourceFile] = Field(default_factory=list)
    skipped: list[ModelSkippedSourceFile] = Field(default_factory=list)
