# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Required repository scan configuration (OMN-21565)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelInvariantAnalysisOverlay"]


class ModelInvariantAnalysisOverlay(BaseModel):
    """Required repository scan configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registry_path: str = Field(description="Registry path relative to scan root")
    lifecycle_path: str = Field(description="Lifecycle path relative to scan root")
    plan_globs: tuple[str, ...] = Field(
        description="Plan selectors relative to scan root"
    )
    exempt_lifecycle_statuses: tuple[str, ...] = Field(
        description="Lifecycle statuses exempting plans"
    )
    always_scopes: tuple[str, ...] = Field(description="Mandatory declared scope tags")
    task_heading_pattern: str = Field(
        description="Task heading expression capturing the task identifier"
    )
    min_reason_length: int = Field(ge=1, description="Minimum stripped reason length")
    denied_placeholders: tuple[str, ...] = Field(
        description="Case insensitive unreasoned placeholders"
    )
    skip_dirs: tuple[str, ...] = Field(
        description="Directory components excluded from scans"
    )
