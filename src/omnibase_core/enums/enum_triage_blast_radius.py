# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Triage blast radius enum (OMN-9322)."""

from __future__ import annotations

from enum import StrEnum


class EnumTriageBlastRadius(StrEnum):
    """Impact scope — drives the third ranking key.

    PLATFORM: org-wide impact (all repos, prod infra).
    REPO: single-repo impact.
    MODULE: single module or service.
    LOCAL: single file / single dev machine.
    """

    PLATFORM = "PLATFORM"
    REPO = "REPO"
    MODULE = "MODULE"
    LOCAL = "LOCAL"

    @property
    def weight(self) -> int:
        weights = {"PLATFORM": 4, "REPO": 3, "MODULE": 2, "LOCAL": 1}
        return weights[self.value]
