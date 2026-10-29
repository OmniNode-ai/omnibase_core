# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Target repo and optional spec path for the requirements consumer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelRequirementsConsumerCheckInput(BaseModel):
    """Repo name, its working tree, and an optional spec override (None = canonical)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str
    repo_root: str
    spec_path: str | None = None
