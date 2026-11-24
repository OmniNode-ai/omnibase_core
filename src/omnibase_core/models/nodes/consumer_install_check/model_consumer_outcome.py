# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The outcome of checking one consumer (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.consumer_install_check.model_consumer_finding import (
    ModelConsumerFinding,
)


class ModelConsumerOutcome(BaseModel):
    """What one consumer checkout did against the candidate."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    consumer: str
    ref: str
    resolved_sha: str = Field(
        default="", description="Commit the consumer checkout resolved to"
    )
    entry_points_imported: int = Field(ge=0)
    tests_collected: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    findings: tuple[ModelConsumerFinding, ...] = ()
    setup_error: str = Field(
        default="",
        description="Set when checkout, venv or install failed before any import",
    )
