# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Triage severity enum (OMN-9322)."""

from __future__ import annotations

from enum import StrEnum


class EnumTriageSeverity(StrEnum):
    """Issue severity — drives the first ranking key.

    Ordering (highest first): CRITICAL > HIGH > MEDIUM > LOW > INFO.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def weight(self) -> int:
        weights = {
            "CRITICAL": 500,
            "HIGH": 400,
            "MEDIUM": 300,
            "LOW": 200,
            "INFO": 100,
        }
        return weights[self.value]
