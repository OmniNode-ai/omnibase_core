"""
TypedDict for handler health check results.

This TypedDict defines the structure returned by handler health_check() methods,
providing typed access to handler health status information.

Related:
    - OMN-230: LocalHandler implementation
    - ProtocolHandler: Handler protocol that may define health_check()

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["TypedDictHealthCheckResult"]

from typing import TypedDict


class TypedDictHealthCheckResult(TypedDict):
    """TypedDict for handler health check results.

    This TypedDict defines the contract for health check results with
    explicit required fields.

    Required Fields:
        dev_test_only: Whether this handler is for dev/test only.
        status: Current health status (e.g., "healthy", "unhealthy").

    Example:
        >>> result: TypedDictHealthCheckResult = {
        ...     "dev_test_only": True,
        ...     "status": "healthy",
        ... }
    """

    dev_test_only: bool
    status: str
