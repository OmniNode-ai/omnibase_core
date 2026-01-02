# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Role Enumeration.

This module defines the architectural role of handlers in the ONEX framework.
While :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType` classifies handlers
by the external system they interact with (HTTP, DATABASE, etc.), and
:class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory` classifies
them by their computational behavior (pure vs impure), EnumHandlerRole classifies them
by their architectural responsibility in the system.

This distinction is critical for:
    - **Routing decisions**: Different roles have different routing semantics
    - **Dependency injection**: Roles determine which container services are available
    - **Lifecycle management**: Roles define initialization and teardown order
    - **Monitoring and observability**: Roles determine metric collection strategies

Location:
    ``omnibase_core.enums.enum_handler_role.EnumHandlerRole``

Import Example:
    .. code-block:: python

        from omnibase_core.enums.enum_handler_role import EnumHandlerRole

        # Or via the enums package
        from omnibase_core.enums import EnumHandlerRole

        # Classify a handler by its architectural role
        role = EnumHandlerRole.NODE_HANDLER
        if role == EnumHandlerRole.INFRA_HANDLER:
            # Apply infrastructure-specific configuration
            pass

See Also:
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      Classifies handlers by external system type (HTTP, DATABASE, etc.)
    - :class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory`:
      Classifies handlers by computational behavior (COMPUTE, EFFECT, etc.)
    - :class:`~omnibase_core.enums.enum_handler_capability.EnumHandlerCapability`:
      Defines capabilities a handler can declare (CACHE, RETRY, etc.)
    - :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:
      Architectural classification of nodes (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)

Note:
    EnumHandlerRole is orthogonal to EnumHandlerType and EnumHandlerTypeCategory.
    A handler has exactly one role, one type, and one category. For example:
        - An HTTP handler processing events: role=NODE_HANDLER, type=HTTP, category=EFFECT
        - A pure transformation handler: role=COMPUTE_HANDLER, type=NAMED, category=COMPUTE

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1086 handler descriptor additions.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


@unique
class EnumHandlerRole(str, Enum):
    """
    Architectural role classification of handlers in the ONEX framework.

    **SINGLE SOURCE OF TRUTH** for handler architectural role classification.

    This enum classifies handlers by their architectural responsibility:

    - **INFRA_HANDLER**: Protocol/transport handlers that manage communication infrastructure
    - **NODE_HANDLER**: Event processing handlers that implement business logic
    - **PROJECTION_HANDLER**: Handlers that read/write projections (read models)
    - **COMPUTE_HANDLER**: Pure computation handlers without side effects

    The four roles form the handler responsibility matrix:

    +---------------------+------------------+------------------+------------------+
    | Role                | Side Effects     | Event Processing | State Management |
    +=====================+==================+==================+==================+
    | INFRA_HANDLER       | Yes (I/O)        | No               | Transport only   |
    +---------------------+------------------+------------------+------------------+
    | NODE_HANDLER        | Yes (via events) | Yes              | Event-driven     |
    +---------------------+------------------+------------------+------------------+
    | PROJECTION_HANDLER  | Yes (R/W)        | Consumes         | Projection state |
    +---------------------+------------------+------------------+------------------+
    | COMPUTE_HANDLER     | No               | No               | None             |
    +---------------------+------------------+------------------+------------------+

    Relationship to EnumNodeKind
    ----------------------------
    EnumHandlerRole aligns with :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:

    - ``INFRA_HANDLER`` -> Typically used by ``EnumNodeKind.EFFECT`` nodes
    - ``NODE_HANDLER`` -> Used by ``EnumNodeKind.REDUCER`` and ``EnumNodeKind.ORCHESTRATOR`` nodes
    - ``PROJECTION_HANDLER`` -> Used by projection services (read model handlers)
    - ``COMPUTE_HANDLER`` -> Used by ``EnumNodeKind.COMPUTE`` nodes

    Example:
        >>> from omnibase_core.enums import EnumHandlerRole
        >>> role = EnumHandlerRole.NODE_HANDLER
        >>> str(role)
        'node_handler'

        >>> # Route based on handler role
        >>> def get_router(role: EnumHandlerRole) -> str:
        ...     match role:
        ...         case EnumHandlerRole.INFRA_HANDLER:
        ...             return "infra_router"
        ...         case EnumHandlerRole.NODE_HANDLER:
        ...             return "event_router"
        ...         case EnumHandlerRole.PROJECTION_HANDLER:
        ...             return "projection_router"
        ...         case EnumHandlerRole.COMPUTE_HANDLER:
        ...             return "compute_router"
        ...         case _ as unreachable:
        ...             EnumHandlerRole.assert_exhaustive(unreachable)
        >>> get_router(EnumHandlerRole.NODE_HANDLER)
        'event_router'

    .. versionadded:: 0.4.0
    """

    INFRA_HANDLER = "infra_handler"
    """Protocol/transport handler. Manages communication infrastructure (HTTP, Kafka, etc.)."""

    NODE_HANDLER = "node_handler"
    """Event processing handler. Implements business logic via event-driven patterns."""

    PROJECTION_HANDLER = "projection_handler"
    """Projection read/write handler. Manages read models and materialized views."""

    COMPUTE_HANDLER = "compute_handler"
    """Pure computation handler. Performs stateless transformations without side effects."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensure exhaustive handling in match statements."""
        # Lazy import to avoid circular dependency with error_codes
        from omnibase_core.errors import ModelOnexError

        raise ModelOnexError(
            message=f"Unhandled enum value: {value}",
            error_code=EnumCoreErrorCode.INVALID_OPERATION,
        )


__all__ = ["EnumHandlerRole"]
