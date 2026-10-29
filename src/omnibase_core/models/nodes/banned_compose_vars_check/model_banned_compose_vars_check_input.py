# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Compose and k8s manifest text plus the banned environment variable names."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelBannedComposeVarsCheckInput(BaseModel):
    """Compose and k8s manifest text plus the banned environment variable names."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    banned: tuple[str, ...] = Field(default_factory=tuple)
    files: tuple[ModelSourceFile, ...] = Field(default_factory=tuple)
