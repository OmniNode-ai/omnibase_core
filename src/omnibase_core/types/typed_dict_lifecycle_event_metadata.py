"""TypedDict for lifecycle event metadata."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictLifecycleEventMetadata(TypedDict, total=False):
    """
    TypedDict for lifecycle event metadata.

    Metadata passed to lifecycle events during node state transitions.
    All fields are optional since different lifecycle events may
    include different metadata.

    Attributes:
        initialization_time_ms: Time taken for initialization in milliseconds
        node_type: Class name of the node
        cleanup_time_ms: Time taken for cleanup in milliseconds
        total_lifetime_ms: Total node lifetime in milliseconds
        final_status: Final status of the node
        initialized_at_ms: Initialization timestamp in milliseconds
        initialization_duration_ms: Duration of initialization
        total_operations: Total number of operations performed
        avg_processing_time_ms: Average processing time
        error_level_count: Number of errors encountered at ERROR severity level
        success_count: Number of successful operations
    """

    initialization_time_ms: NotRequired[float]
    node_type: NotRequired[str]
    cleanup_time_ms: NotRequired[float]
    total_lifetime_ms: NotRequired[float]
    final_status: NotRequired[str]
    initialized_at_ms: NotRequired[float]
    initialization_duration_ms: NotRequired[float]
    total_operations: NotRequired[float]
    avg_processing_time_ms: NotRequired[float]
    error_level_count: NotRequired[float]
    success_count: NotRequired[float]


__all__ = ["TypedDictLifecycleEventMetadata"]
