# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumRetryType(StrEnum):
    """Retry strategy for overseer task routing decisions."""

    NONE = "none"
    """No retry — fail immediately on first error."""

    IMMEDIATE = "immediate"
    """Retry immediately without delay."""

    BACKOFF = "backoff"
    """Exponential backoff between retries."""

    ESCALATE = "escalate"
    """Escalate to a higher-capability model on retry."""


__all__: list[str] = ["EnumRetryType"]
