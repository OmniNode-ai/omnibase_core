from __future__ import annotations

from typing import Dict, TypedDict

"""
TypedDict for node execution settings summary.

Replaces dict[str, int | bool | None] return type with structured typing.
"""


from typing import TypedDict


class ModelNodeExecutionSummaryType(TypedDict):
    """
    Typed dict[str, Any]ionary for node execution settings summary.

    Replaces dict[str, int | bool | None] return type from get_execution_summary()
    with proper type structure.
    """

    max_retries: int | None
    timeout_seconds: int | None
    batch_size: int | None
    parallel_execution: bool
    has_retry_limit: bool
    has_timeout: bool
    supports_batching: bool


# Export for use
__all__ = ["ModelNodeExecutionSummaryType"]
