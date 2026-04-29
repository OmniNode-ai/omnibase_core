# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hotspot topic model — a topic appearing in multiple contract overlap edges."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelHotspotTopic(BaseModel):
    """A topic that appears in multiple contract overlap edges."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str
    overlap_count: int
    node_refs: list[str]
