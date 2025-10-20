"""TypedDict for node execution settings summary.

Type-safe dictionary for node execution configuration.
"""

from typing import TypedDict


class TypedDictNodeExecutionSummary(TypedDict):
    """Typed dictionary for node execution settings summary.

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


__all__ = ["TypedDictNodeExecutionSummary"]
