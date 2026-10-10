# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kafka topic registry for the Review-Fix Pairing subsystem.

All topic names follow the ONEX canonical format::

    onex.{kind}.{producer}.{event-name}.v{n}

where:
    kind     — ``evt`` for domain events, ``cmd`` for commands
    producer — ``review-pairing`` for this subsystem
    event-name — kebab-case event name
    n        — integer version

This module is the single source of truth for Review-Fix Pairing topic names.
No hardcoded topic strings should appear in producer or consumer code; use
these enum values instead.

Topics:
    FINDING_OBSERVED  — A review finding was captured from any review source.
    FIX_APPLIED       — A fix commit was applied for a known finding.
    FINDING_RESOLVED  — A finding disappearance was confirmed post-fix.
    PAIR_CREATED      — A confidence-scored finding-fix pair was created.

Reference: OMN-2535
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class ReviewPairingTopic(StrEnum):
    """Canonical Kafka topic names for the Review-Fix Pairing subsystem.

    All topics use ``onex.evt.review-pairing.*`` as the producer namespace.

    Values:
        FINDING_OBSERVED: Fired when a review finding is captured from any
            review source (linter, CI, GitHub Checks). Published by the Review
            Signal Adapters; consumed by the Pairing Engine.
        FIX_APPLIED: Fired when a fix commit is applied for a known finding.
            Published by the Review Signal Adapters; consumed by the Pairing Engine.
        FINDING_RESOLVED: Fired when a finding disappearance is confirmed by
            a post-fix CI run. Published by the Finding Disappearance Verifier;
            consumed by the Pairing Engine and Pattern Candidate Reducer.
        PAIR_CREATED: Fired when a confidence-scored finding-fix pair is created.
            Published by the Pairing Engine; consumed by the Pattern Candidate
            Reducer and metrics collectors.
    """

    FINDING_OBSERVED = "onex.evt.review-pairing.finding-observed.v1"
    """A review finding was captured from any review source."""

    FIX_APPLIED = "onex.evt.review-pairing.fix-applied.v1"
    """A fix commit was applied for a known finding."""

    FINDING_RESOLVED = "onex.evt.review-pairing.finding-resolved.v1"
    """A finding disappearance was confirmed post-fix."""

    PAIR_CREATED = "onex.evt.review-pairing.pair-created.v1"
    """A confidence-scored finding-fix pair was created."""

    CALIBRATION_RUN_COMPLETED = "onex.evt.review-pairing.calibration-run-completed.v1"
    """A calibration run completed with metrics for a challenger model."""
