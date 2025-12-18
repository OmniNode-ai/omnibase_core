"""
TypedDict for load balancer statistics.

Used by ModelLoadBalancer.get_stats() method.
"""

from typing import TypedDict


class TypedDictLoadBalancerStats(TypedDict, total=True):
    """
    TypedDict for load balancer statistics.

    Used for ModelLoadBalancer.get_stats() return type.

    Attributes:
        active_operations: Current number of active operations
        max_concurrent: Maximum number of concurrent operations allowed
        utilization: Current utilization as a ratio (active/max)
        total_operations: Total number of operations processed
    """

    active_operations: int
    max_concurrent: int
    utilization: float
    total_operations: int


__all__ = ["TypedDictLoadBalancerStats"]
