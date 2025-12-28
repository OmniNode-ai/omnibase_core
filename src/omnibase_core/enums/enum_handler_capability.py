# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Capability Enumeration.

This module defines unified handler capabilities that span all node types in the ONEX
framework. Capabilities are declarative flags that handlers can advertise to indicate
what features they support (caching, retry, batching, etc.).

Capabilities enable:
    - **Capability-based routing**: Route requests to handlers that support required features
    - **Runtime optimization**: Enable caching, batching, or streaming based on declared capabilities
    - **Validation**: Verify handlers meet requirements before execution
    - **Documentation**: Self-documenting handlers via declared capabilities

Handler capabilities vs Node-specific capabilities:
    - ``EnumHandlerCapability`` (this enum): Cross-cutting capabilities applicable to ANY handler
    - ``EnumComputeCapability``: COMPUTE-specific capabilities (transformation, validation)
    - ``EnumEffectCapability``: EFFECT-specific capabilities (transactional, idempotent I/O)
    - ``EnumReducerCapability``: REDUCER-specific capabilities (FSM, aggregation)
    - ``EnumOrchestratorCapability``: ORCHESTRATOR-specific capabilities (workflow, saga)

Location:
    ``omnibase_core.enums.enum_handler_capability.EnumHandlerCapability``

Import Example:
    .. code-block:: python

        from omnibase_core.enums.enum_handler_capability import EnumHandlerCapability

        # Or via the enums package
        from omnibase_core.enums import EnumHandlerCapability

        # Declare handler capabilities
        capabilities = [
            EnumHandlerCapability.CACHE,
            EnumHandlerCapability.IDEMPOTENT,
            EnumHandlerCapability.RETRY,
        ]

        # Check if handler supports caching
        if EnumHandlerCapability.CACHE in handler.capabilities:
            result = cache.get_or_compute(key, handler.execute)

See Also:
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      Classifies handlers by external system type (HTTP, DATABASE, etc.)
    - :class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory`:
      Classifies handlers by computational behavior (COMPUTE, EFFECT)
    - :class:`~omnibase_core.enums.enum_handler_command_type.EnumHandlerCommandType`:
      Command types for handler operations (EXECUTE, VALIDATE, etc.)
    - :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:
      Architectural classification of nodes (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1085 handler enum additions.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumHandlerCapability(str, Enum):
    """
    Unified handler capabilities that apply across all node types.

    **SINGLE SOURCE OF TRUTH** for cross-cutting handler capabilities.

    These capabilities apply to handlers of any :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`
    (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR). They represent features that the handler runtime
    can leverage for optimization, routing, and validation.

    Capability Compatibility Matrix
    -------------------------------
    Not all capabilities make sense for all handler categories:

    +-------------+------------+------------+------------------------+
    | Capability  | COMPUTE    | EFFECT     | NONDETERMINISTIC       |
    +=============+============+============+========================+
    | TRANSFORM   | Yes        | Yes        | Yes                    |
    +-------------+------------+------------+------------------------+
    | VALIDATE    | Yes        | Yes        | Yes                    |
    +-------------+------------+------------+------------------------+
    | CACHE       | Yes        | Caution*   | No                     |
    +-------------+------------+------------+------------------------+
    | RETRY       | Yes        | Caution*   | Yes                    |
    +-------------+------------+------------+------------------------+
    | BATCH       | Yes        | Yes        | Yes                    |
    +-------------+------------+------------+------------------------+
    | STREAM      | Yes        | Yes        | Yes                    |
    +-------------+------------+------------+------------------------+
    | ASYNC       | Yes        | Yes        | Yes                    |
    +-------------+------------+------------+------------------------+
    | IDEMPOTENT  | Always     | Must check | Always                 |
    +-------------+------------+------------+------------------------+

    *Caution: EFFECT handlers with CACHE or RETRY should also declare IDEMPOTENT.

    For node-specific capabilities, see:
        - ``EnumComputeCapability`` - COMPUTE node capabilities
        - ``EnumEffectCapability`` - EFFECT node capabilities
        - ``EnumReducerCapability`` - REDUCER node capabilities
        - ``EnumOrchestratorCapability`` - ORCHESTRATOR node capabilities

    Example:
        >>> from omnibase_core.enums import EnumHandlerCapability
        >>> cap = EnumHandlerCapability.CACHE
        >>> str(cap)
        'cache'

        >>> # Build a capability set for a cacheable, retryable handler
        >>> capabilities = {
        ...     EnumHandlerCapability.CACHE,
        ...     EnumHandlerCapability.RETRY,
        ...     EnumHandlerCapability.IDEMPOTENT,
        ... }
        >>> EnumHandlerCapability.CACHE in capabilities
        True

    .. versionadded:: 0.4.0
    """

    TRANSFORM = "transform"
    """Can transform data between formats."""

    VALIDATE = "validate"
    """Can validate input/output data."""

    CACHE = "cache"
    """Supports caching of results for performance."""

    RETRY = "retry"
    """Supports automatic retry on transient failures."""

    BATCH = "batch"
    """Supports batch processing of multiple items."""

    STREAM = "stream"
    """Supports streaming data processing."""

    ASYNC = "async"
    """Supports asynchronous execution."""

    IDEMPOTENT = "idempotent"
    """Operation is idempotent (can safely retry without side effects)."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling in match statements."""
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerCapability"]
