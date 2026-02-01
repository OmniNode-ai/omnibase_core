"""
Execution Order Enum.

Strongly typed enumeration for execution order strategies.
Replaces Literal["reverse", "forward", "parallel"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumExecutionOrder(StrValueHelper, str, Enum):
    """
    Strongly typed execution order discriminators.

    Used for workflow and compensation action ordering to specify
    the sequence in which actions should be executed. Inherits from str
    for JSON serialization compatibility while providing type safety
    and IDE support.
    """

    REVERSE = "reverse"
    FORWARD = "forward"
    PARALLEL = "parallel"

    # Classification constants moved outside enum definition to avoid MyPy errors

    @classmethod
    def is_sequential(cls, order: EnumExecutionOrder) -> bool:
        """Check if the execution order is sequential."""
        return order in SEQUENTIAL_ORDERS

    @classmethod
    def is_concurrent(cls, order: EnumExecutionOrder) -> bool:
        """Check if the execution order allows concurrency."""
        return order in CONCURRENT_ORDERS

    @classmethod
    def preserves_dependency_order(cls, order: EnumExecutionOrder) -> bool:
        """Check if the execution order preserves dependency relationships."""
        return order in SEQUENTIAL_ORDERS

    @classmethod
    def requires_synchronization(cls, order: EnumExecutionOrder) -> bool:
        """Check if the execution order requires synchronization mechanisms."""
        return order == cls.PARALLEL

    @classmethod
    def is_rollback_friendly(cls, order: EnumExecutionOrder) -> bool:
        """Check if the execution order is suitable for rollback operations."""
        return order == cls.REVERSE

    @classmethod
    def get_order_description(cls, order: EnumExecutionOrder) -> str:
        """Get a human-readable description of the execution order."""
        descriptions = {
            cls.REVERSE: "Execute actions in reverse dependency order",
            cls.FORWARD: "Execute actions in forward dependency order",
            cls.PARALLEL: "Execute actions concurrently where possible",
        }
        return descriptions.get(order, "Unknown execution order")

    @classmethod
    def get_typical_use_case(cls, order: EnumExecutionOrder) -> str:
        """Get typical use case for each execution order."""
        use_cases = {
            cls.REVERSE: "Compensation actions, cleanup operations",
            cls.FORWARD: "Normal workflow execution, initialization",
            cls.PARALLEL: "Independent operations, performance optimization",
        }
        return use_cases.get(order, "Unknown use case")

    @classmethod
    def get_performance_characteristics(cls, order: EnumExecutionOrder) -> str:
        """Get performance characteristics of the execution order."""
        characteristics = {
            cls.REVERSE: "Sequential, deterministic, rollback-safe",
            cls.FORWARD: "Sequential, deterministic, efficient",
            cls.PARALLEL: "Concurrent, high-throughput, complex synchronization",
        }
        return characteristics.get(order, "Unknown characteristics")


# Classification sets - defined outside enum to avoid MyPy issues
SEQUENTIAL_ORDERS: frozenset[EnumExecutionOrder] = frozenset(
    [EnumExecutionOrder.REVERSE, EnumExecutionOrder.FORWARD],
)
CONCURRENT_ORDERS: frozenset[EnumExecutionOrder] = frozenset(
    [EnumExecutionOrder.PARALLEL],
)

# Export for use
__all__ = ["CONCURRENT_ORDERS", "SEQUENTIAL_ORDERS", "EnumExecutionOrder"]
