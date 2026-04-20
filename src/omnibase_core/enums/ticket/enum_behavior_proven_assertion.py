# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumBehaviorProvenAssertion — outcome of a live-state behavior probe."""

from __future__ import annotations

from enum import StrEnum


class EnumBehaviorProvenAssertion(StrEnum):
    """Outcome of a behavior_proven DoD evidence probe.

    Used by `ModelBehaviorProvenReceipt` to declare whether the recorded
    command+query combination observed the expected live state. Absence
    of a receipt is treated identically to FAILED by downstream gates
    (OMN-9279 DoD guard, OMN-9281 CI gate).
    """

    PASSED = "passed"
    FAILED = "failed"


__all__ = ["EnumBehaviorProvenAssertion"]
