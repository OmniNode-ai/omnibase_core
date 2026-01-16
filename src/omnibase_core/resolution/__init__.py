"""
Resolution Module for ONEX Framework.

This module provides execution order resolution for handler contracts based
on execution profiles and constraints. The resolver computes a deterministic
execution plan from declarative constraints.

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ProtocolExecutionResolver: The protocol interface

.. versionadded:: 0.4.1
"""

from omnibase_core.resolution.resolver_execution import ExecutionResolver

__all__ = [
    "ExecutionResolver",
]
