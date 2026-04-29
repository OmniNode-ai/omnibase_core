# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dependency snapshot model — a single dependency graph observation."""

from __future__ import annotations

from datetime import (
    datetime,
)

from pydantic import BaseModel, ConfigDict


class ModelDependencySnapshot(BaseModel):
    """A single dependency graph observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observed_at: datetime
    edge_count: int
    wave_count: int
    hotspot_count: int
