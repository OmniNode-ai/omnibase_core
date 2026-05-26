# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Retry strategy enum for routing policy decisions."""

from enum import StrEnum


class EnumRetryType(StrEnum):
    """Retry strategy for the selected routing model."""

    NONE = "none"
    SAME_MODEL = "same_model"
    ESCALATE_TIER = "escalate_tier"
    FALLBACK_MODEL = "fallback_model"


__all__: list[str] = ["EnumRetryType"]
