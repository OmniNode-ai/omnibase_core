# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Triage freshness enum (OMN-9322)."""

from __future__ import annotations

from enum import StrEnum


class EnumTriageFreshness(StrEnum):
    """Evidence freshness — drives the second ranking key.

    LIVE: probed this run, high confidence.
    RECENT: cached artifact <24h.
    STALE: cached artifact 24h-72h.
    MISSING: no data available.
    """

    LIVE = "LIVE"
    RECENT = "RECENT"
    STALE = "STALE"
    MISSING = "MISSING"

    @property
    def weight(self) -> int:
        weights = {"LIVE": 40, "RECENT": 30, "STALE": 20, "MISSING": 10}
        return weights[self.value]
