from __future__ import annotations

"""
TypedDict for discovery responder statistics.
"""

from typing import TypedDict


class TypedDictDiscoveryStats(TypedDict):
    """TypedDict for discovery responder statistics."""

    requests_received: int
    responses_sent: int
    throttled_requests: int
    last_request_time: float | None
    error_count: int
