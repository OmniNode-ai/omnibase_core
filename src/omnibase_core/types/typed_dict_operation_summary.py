"""
TypedDict for event bus operation summary data.

Provides type safety for operation summary dictionaries used in event bus
input/output state monitoring and logging.
"""

from typing import TypedDict


class TypedDictOperationSummary(TypedDict):
    """
    Typed dictionary for operation summary data.

    Used by ModelEventBusInputOutputState.get_operation_summary() to provide
    structured operation status information for logging and monitoring.
    """

    input_version: str  # string-version-ok: TypedDict at serialization boundary for logging/monitoring
    output_version: str  # string-version-ok: TypedDict at serialization boundary for logging/monitoring
    status: str
    message: str
    version_match: bool
    successful: bool


__all__ = ["TypedDictOperationSummary"]
