"""TypedDict for node capabilities summary.

Type-safe dictionary for node capabilities information.
"""

from typing import TypedDict


class TypedDictNodeCapabilitiesSummary(TypedDict):
    """Typed dictionary for node capabilities info summary.

    Replaces dict[str, Any] return type from get_capabilities_summary()
    with proper type structure.
    """

    capabilities_count: int
    operations_count: int
    dependencies_count: int
    has_capabilities: bool
    has_operations: bool
    has_dependencies: bool
    has_performance_metrics: bool
    primary_capability: str | None
    metrics_count: int


__all__ = ["TypedDictNodeCapabilitiesSummary"]
