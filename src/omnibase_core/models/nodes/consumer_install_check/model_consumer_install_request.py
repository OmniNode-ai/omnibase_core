# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Request of the consumer install check (OMN-26670)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelConsumerInstallRequest(BaseModel):
    """The candidate build to install and the overlay that says into what."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    candidate_distribution: str = Field(min_length=1)
    candidate_spec: str = Field(
        min_length=1, description="pip requirement or wheel path of the candidate build"
    )
    overlay_path: Path
    work_dir: Path
    consumer_ref_overrides: tuple[tuple[str, str], ...] = Field(
        default=(),
        description="(consumer name, ref) pairs replacing the overlay ref, for a replay at a recorded sha",
    )
