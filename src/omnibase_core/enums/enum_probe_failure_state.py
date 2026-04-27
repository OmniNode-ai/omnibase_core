# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe failure state enumeration.

Enumerates the four failure modes a runtime aliveness probe can land in,
per the runtime-lifecycle-hardening plan, Wave 3 / Task 9 probe contract.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumProbeFailureState"]


@unique
class EnumProbeFailureState(StrValueHelper, str, Enum):
    """Failure modes recorded on a ModelRuntimeAlivenessProbeReceipt.

    Sampling order is sequential: publish probe -> observe terminal event ->
    observe projection row -> sample consumer-group lag. Each entry below maps
    to a step that did not satisfy the probe contract at the corresponding
    sampling point.
    """

    TIMEOUT = "timeout"
    TERMINAL_FAILURE_EMITTED = "terminal_failure_emitted"
    PROJECTION_WRITE_FAILED = "projection_write_failed"
    LAG_ABOVE_THRESHOLD = "lag_above_threshold"
