# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumSuppressionDecision: governs whether a log entry is withheld from the bus.

Canonical enum for OMN-13703 ModelStructuredLogEntry schema unification.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumSuppressionDecision(UtilStrValueHelper, str, Enum):
    """Decision on whether to suppress (withhold) a log entry from the bus."""

    EMIT = "emit"
    """Entry is allowed through; no suppression applied."""

    SUPPRESS_BELOW_THRESHOLD = "suppress_below_threshold"
    """Entry withheld because its log level is below the configured threshold."""

    SUPPRESS_RATE_LIMITED = "suppress_rate_limited"
    """Entry withheld because the emitter exceeded its per-interval rate limit."""

    SUPPRESS_POLICY = "suppress_policy"
    """Entry withheld by an explicit suppression policy rule."""


__all__ = ["EnumSuppressionDecision"]
