# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Repo roots consumed by the demo-path topic coherence validator."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelDemoPathTopicCoherenceCheckInput(BaseModel):
    """Repo roots scanned for demo-path contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_roots: tuple[Path, ...]
