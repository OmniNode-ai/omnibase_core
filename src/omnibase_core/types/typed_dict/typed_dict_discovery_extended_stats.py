"""TypedDict for extended discovery stats including active status."""

from __future__ import annotations

from typing import TypedDict


class TypedDictDiscoveryExtendedStats(TypedDict):
    """TypedDict for extended discovery stats including active status."""

    requests_received: int
    responses_sent: int
    throttled_requests: int
    filtered_requests: int
    last_request_time: float | None
    error_level_count: int
    active: bool
    throttle_seconds: float
    last_response_time: float | None


__all__ = ["TypedDictDiscoveryExtendedStats"]
