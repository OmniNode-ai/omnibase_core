# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Operational disposition of a delegation terminal."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationOperationalOutcome(StrEnum):
    """The runtime event that produced the final terminal.

    ``QUALITY_REJECTED`` is the generic outcome for a failed content gate.  It
    does not assert whether a deterministic, heuristic, or legacy-unclassified
    rule caused that rejection.
    """

    COMPLETED = "completed"
    REFUSED = "refused"
    SCHEMA_REJECTED = "schema_rejected"
    QUALITY_REJECTED = "quality_rejected"
    PROVIDER_QUOTA = "provider_quota"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    BOUNDARY_FAILURE = "boundary_failure"
    INFERENCE_FAILED = "inference_failed"
    TERMINAL_CONSTRUCTION_FAILED = "terminal_construction_failed"


__all__ = ["EnumDelegationOperationalOutcome"]
