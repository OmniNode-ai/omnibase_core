"""
TypedDict for discovery responder statistics.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictDiscoveryStats(TypedDict):
    """
    TypedDict for discovery responder statistics.

    Attributes:
        requests_received: Total discovery requests received
        responses_sent: Total discovery responses sent
        throttled_requests: Requests throttled due to rate limiting
        filtered_requests: Requests that didn't match discovery criteria (node type, capabilities, filters)
        last_request_time: Timestamp of last request received (None if no requests)
        error_level_count: Count of errors during discovery processing (message parsing, response publishing, etc.)
    """

    requests_received: int
    responses_sent: int
    throttled_requests: int
    filtered_requests: int
    last_request_time: float | None
    error_level_count: int


__all__ = ["TypedDictDiscoveryStats"]
