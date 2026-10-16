# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the public-repository runner placement check (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelPublicRunnerPlacementInput"]


class ModelPublicRunnerPlacementInput(BaseModel):
    """A repository's workflow files, optionally its base, and its baselined jobs.

    Attributes:
        repository: The repository name the baseline is keyed on.
        public: False means a private repository, where self-hosted runners are
            the rule and the check passes.
        files: Repository-relative (path, source) pairs of the head workflows.
        base_files: The same pairs at the change's base, or None when no base is
            known (a push, a staged-files run); the re-added-job rule is then off.
        baseline: ``(path, job)`` pairs of this repository the baseline records.
        report_stale_baseline: When True (a full-tree scan), a baseline entry no
            workflow produces any more is reported as WARN.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(min_length=1)
    public: bool = True
    files: tuple[ModelSourceFile, ...] = Field(default=())
    base_files: tuple[ModelSourceFile, ...] | None = None
    baseline: frozenset[tuple[str, str]] = Field(default=frozenset())
    report_stale_baseline: bool = False
