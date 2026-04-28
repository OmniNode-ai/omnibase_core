# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumVerifierVerdict(StrEnum):
    """Verdict from the deterministic verification layer.

    Each verdict maps to a routing action in the overseer:
    - PASS: proceed to next stage
    - FAIL: halt and report
    - RETRY_REQUIRED: re-run with adjusted parameters
    - ESCALATE: route to higher-tier agent or human
    """

    PASS = "PASS"
    """All checks passed — proceed."""

    FAIL = "FAIL"
    """One or more critical checks failed — halt."""

    RETRY_REQUIRED = "RETRY_REQUIRED"
    """Transient failure detected — retry with backoff."""

    ESCALATE = "ESCALATE"
    """Verification inconclusive — escalate to higher tier."""


__all__: list[str] = ["EnumVerifierVerdict"]
