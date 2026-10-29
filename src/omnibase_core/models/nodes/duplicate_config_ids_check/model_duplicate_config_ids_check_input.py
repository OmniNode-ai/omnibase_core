# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Manifest location consumed by the duplicate-config-ids validator."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelDuplicateConfigIdsCheckInput(BaseModel):
    """Manifest path and the repo root its registry paths are relative to."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest_path: Path
    repo_root: Path
