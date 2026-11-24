# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One command the consumer install check runs (OMN-26670)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelCommandRequest(BaseModel):
    """An argv, where it runs and how long it may take."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    argv: tuple[str, ...] = Field(min_length=1)
    cwd: Path | None = None
    timeout_seconds: float = Field(gt=0)
