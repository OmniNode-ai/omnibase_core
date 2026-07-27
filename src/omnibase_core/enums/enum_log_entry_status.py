# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumLogEntryStatus: lifecycle status of a structured log entry.

Canonical enum for OMN-13703 ModelStructuredLogEntry schema unification.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumLogEntryStatus(UtilStrValueHelper, str, Enum):
    """Lifecycle status of a ModelStructuredLogEntry on the event bus."""

    EMITTED = "emitted"
    """Entry successfully published to the bus."""

    SUPPRESSED = "suppressed"
    """Entry was evaluated but withheld from the bus per SuppressionDecision."""

    REDACTED = "redacted"
    """Entry was published with sensitive fields replaced per RedactionState."""

    FAILED = "failed"
    """Attempt to publish the entry failed."""


__all__ = ["EnumLogEntryStatus"]
