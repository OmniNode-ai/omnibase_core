# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Type Category Enumeration.

This module defines the behavioral classification of handlers in the ONEX framework.
While :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType` classifies handlers
by the external system they interact with (HTTP, DATABASE, etc.), EnumHandlerTypeCategory
classifies them by their computational behavior (pure vs impure, deterministic vs non-deterministic).

This distinction is critical for:
    - **Caching decisions**: COMPUTE handlers can be safely cached; EFFECT handlers cannot
    - **Retry policies**: EFFECT handlers may need idempotency checks; COMPUTE handlers can retry freely
    - **Testing strategies**: COMPUTE handlers need no mocking; EFFECT handlers require stubs
    - **Parallelization**: COMPUTE handlers can run in parallel without coordination

Location:
    ``omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory``

Import Example:
    .. code-block:: python

        from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory

        # Or via the enums package
        from omnibase_core.enums import EnumHandlerTypeCategory

        # Classify a handler
        category = EnumHandlerTypeCategory.COMPUTE
        if category == EnumHandlerTypeCategory.EFFECT:
            # Apply retry policy with idempotency check
            pass

See Also:
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      Classifies handlers by external system type (HTTP, DATABASE, etc.)
    - :class:`~omnibase_core.enums.enum_handler_capability.EnumHandlerCapability`:
      Defines capabilities a handler can declare (CACHE, RETRY, etc.)
    - :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:
      Architectural classification of nodes (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)
    - :class:`~omnibase_core.enums.enum_handler_command_type.EnumHandlerCommandType`:
      Command types for handler operations (EXECUTE, VALIDATE, etc.)

Note:
    ADAPTER is NOT a category--it's a policy tag applied at the descriptor level.
    See ``ModelHandlerDescriptor`` for adapter configuration.

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1085 handler enum additions.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn


@unique
class EnumHandlerTypeCategory(str, Enum):
    """
    Behavioral classification of handlers in the ONEX framework.

    **SINGLE SOURCE OF TRUTH** for handler behavioral classification.

    This enum classifies handlers by their computational behavior:

    - **Pure vs Impure**: Does the handler have side effects?
    - **Deterministic vs Non-deterministic**: Does the same input always produce the same output?

    The three categories form a decision matrix:

    +---------------------------+---------------+-------------------+
    | Category                  | Pure (no I/O) | Deterministic     |
    +===========================+===============+===================+
    | COMPUTE                   | Yes           | Yes               |
    +---------------------------+---------------+-------------------+
    | NONDETERMINISTIC_COMPUTE  | Yes           | No                |
    +---------------------------+---------------+-------------------+
    | EFFECT                    | No            | N/A (has I/O)     |
    +---------------------------+---------------+-------------------+

    Relationship to EnumNodeKind
    ----------------------------
    EnumHandlerTypeCategory aligns with :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:

    - ``COMPUTE`` category -> ``EnumNodeKind.COMPUTE`` nodes
    - ``NONDETERMINISTIC_COMPUTE`` category -> ``EnumNodeKind.COMPUTE`` nodes (with caching disabled)
    - ``EFFECT`` category -> ``EnumNodeKind.EFFECT`` nodes

    Note: ADAPTER is NOT a category--it's a policy tag. See ``ModelHandlerDescriptor``.

    Example:
        >>> from omnibase_core.enums import EnumHandlerTypeCategory
        >>> cat = EnumHandlerTypeCategory.COMPUTE
        >>> str(cat)
        'compute'

        >>> # Check if handler can be cached
        >>> def can_cache(category: EnumHandlerTypeCategory) -> bool:
        ...     return category == EnumHandlerTypeCategory.COMPUTE
        >>> can_cache(EnumHandlerTypeCategory.COMPUTE)
        True
        >>> can_cache(EnumHandlerTypeCategory.EFFECT)
        False

    .. versionadded:: 0.4.0
    """

    COMPUTE = "compute"
    """Pure, deterministic handler. Same input always produces same output."""

    EFFECT = "effect"
    """Side-effecting I/O handler. Interacts with external systems (files, network, database)."""

    NONDETERMINISTIC_COMPUTE = "nondeterministic_compute"
    """Pure but non-deterministic handler. No side effects but output varies (e.g., random, time-based)."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def values(cls) -> list[str]:
        """Return all values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensure exhaustive handling in match statements.

        Uses AssertionError instead of ModelOnexError to avoid
        circular imports in the enum module.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumHandlerTypeCategory"]
