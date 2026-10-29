# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Repo label and inline source files for the url-authority scanner."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelUrlAuthorityCheckInput(BaseModel):
    """Repo name for fingerprints and the repo-relative (path, source) pairs to scan."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str
    files: tuple[ModelSourceFile, ...] = ()
