"""
Resolution Module for ONEX Framework.

This module provides execution order resolution for handler contracts based
on execution profiles and constraints. The resolver computes a deterministic
execution plan from declarative constraints.

Components:
    - ExecutionResolver: Topological ordering of handlers from constraints
    - resolve_handler: Import path resolution for handler callables
    - clear_handler_cache: Cache management for handler resolution
    - HandlerCallable: Protocol type for resolved handlers
    - LazyLoader: Type alias for lazy import functions
    - resolve_protocol_dependencies: Contract-driven protocol dependency resolution

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - OMN-1731: Contract-driven zero-code node base classes
    - ProtocolExecutionResolver: The protocol interface

.. versionadded:: 0.4.1
"""

from omnibase_core.resolution.resolver_execution import ExecutionResolver
from omnibase_core.resolution.resolver_handler import (
    HandlerCallable,
    LazyLoader,
    clear_handler_cache,
    resolve_handler,
)
from omnibase_core.resolution.resolver_protocol_dependency import (
    resolve_protocol_dependencies,
)

__all__ = [
    "ExecutionResolver",
    "HandlerCallable",
    "LazyLoader",
    "clear_handler_cache",
    "resolve_handler",
    "resolve_protocol_dependencies",
]
