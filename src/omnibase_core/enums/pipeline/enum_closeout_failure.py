# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closeout failure reason enum for pipeline verification."""

from enum import StrEnum, unique

__all__ = ["EnumCloseoutFailure"]


@unique
class EnumCloseoutFailure(StrEnum):
    """Reason a closeout verification failed."""

    OBSERVED_CHAIN_MISSING = "observed_chain_missing"
    CHAIN_EVENT_MISSING = "chain_event_missing"
    CHAIN_ORDER_MISMATCH = "chain_order_mismatch"
    UNEXPECTED_EVENT = "unexpected_event"
    EVIDENCE_MISSING = "evidence_missing"
    EVIDENCE_HASH_MISMATCH = "evidence_hash_mismatch"
    TESTS_FAILED = "tests_failed"
    VERIFIER_MISSING = "verifier_missing"
