# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSweepResult — structured result from a sweep skill run."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSweepResult(BaseModel):
    """Structured result from a sweep skill run.

    Emitted by sweep nodes after each run and projected into the sweep_results
    table by the omnidash read-model consumer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Semantic version of the sweep-result wire schema.",
    )
    sweep_type: Literal[
        "aislop",
        "coverage",
        "compliance",
        "contract",
        "dashboard",
        "runtime",
        "data_flow",
    ]
    session_id: UUID
    correlation_id: str
    ran_at: datetime
    duration_seconds: float
    passed: bool
    finding_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    repos_scanned: tuple[str, ...] = Field(default_factory=tuple)
    summary: str
    output_path: str | None = None


__all__: list[str] = ["ModelSweepResult"]
