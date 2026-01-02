# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Command Type Enumeration.

This module defines typed command identifiers for handler operations in the ONEX framework.
Using an enum instead of raw strings provides compile-time safety, IDE autocompletion,
and exhaustiveness checking in match statements.

Design Rationale:
    - **Type Safety**: Prevents typos like "execute" vs "Execute" vs "EXECUTE"
    - **IDE Support**: Full autocompletion and type hints in modern IDEs
    - **Exhaustiveness**: Python type checkers can verify all cases are handled
    - **Centralization**: Single source of truth for all command types
    - **Serialization**: String values for JSON/YAML compatibility

Command Lifecycle:
    1. ``VALIDATE`` - Check inputs are valid (optional, can be implicit in EXECUTE)
    2. ``DRY_RUN`` - Simulate execution without side effects (optional)
    3. ``EXECUTE`` - Primary handler operation
    4. ``ROLLBACK`` - Undo operation if needed (optional, EFFECT handlers only)

Introspection Commands:
    - ``DESCRIBE`` - Get handler metadata and capabilities
    - ``HEALTH_CHECK`` - Verify handler is operational
    - ``CONFIGURE`` - Update handler configuration
    - ``RESET`` - Reset handler to initial state

Location:
    ``omnibase_core.enums.enum_handler_command_type.EnumHandlerCommandType``

Import Example:
    .. code-block:: python

        from omnibase_core.enums.enum_handler_command_type import EnumHandlerCommandType

        # Or via the enums package
        from omnibase_core.enums import EnumHandlerCommandType

        # Dispatch handler command
        match command:
            case EnumHandlerCommandType.EXECUTE:
                result = handler.execute(input_data)
            case EnumHandlerCommandType.VALIDATE:
                errors = handler.validate(input_data)
            case EnumHandlerCommandType.DRY_RUN:
                preview = handler.dry_run(input_data)
            case _:
                EnumHandlerCommandType.assert_exhaustive(command)

See Also:
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      Classifies handlers by external system type (HTTP, DATABASE, etc.)
    - :class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory`:
      Classifies handlers by computational behavior (COMPUTE, EFFECT)
    - :class:`~omnibase_core.enums.enum_handler_capability.EnumHandlerCapability`:
      Defines capabilities a handler can declare (CACHE, RETRY, etc.)
    - :class:`~omnibase_core.enums.enum_node_kind.EnumNodeKind`:
      Architectural classification of nodes (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1085 handler enum additions.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


@unique
class EnumHandlerCommandType(str, Enum):
    """
    Typed command identifiers for handler operations.

    **SINGLE SOURCE OF TRUTH** for handler command types.

    This enum replaces magic strings in handler command dispatching, providing:
        - **Type safety**: Prevents typos ("execute" vs "Execute")
        - **IDE autocompletion**: Full support in modern IDEs
        - **Exhaustiveness checking**: Type checkers verify all cases handled
        - **Centralized definitions**: Single source of truth for all command types
        - **Serialization**: String values for JSON/YAML compatibility

    Command Categories
    ------------------

    **Execution Commands** (primary operations):
        - ``EXECUTE`` - Run the handler's main operation
        - ``VALIDATE`` - Check inputs without executing
        - ``DRY_RUN`` - Simulate execution, show what would happen
        - ``ROLLBACK`` - Undo a previous operation (EFFECT handlers only)

    **Introspection Commands** (metadata and health):
        - ``DESCRIBE`` - Return handler capabilities and metadata
        - ``HEALTH_CHECK`` - Verify handler is operational

    **Configuration Commands** (state management):
        - ``CONFIGURE`` - Update handler settings
        - ``RESET`` - Restore handler to initial state

    Command Applicability by Handler Category
    -----------------------------------------

    +---------------+------------+------------+------------------------+
    | Command       | COMPUTE    | EFFECT     | NONDETERMINISTIC       |
    +===============+============+============+========================+
    | EXECUTE       | Yes        | Yes        | Yes                    |
    +---------------+------------+------------+------------------------+
    | VALIDATE      | Yes        | Yes        | Yes                    |
    +---------------+------------+------------+------------------------+
    | DRY_RUN       | Yes        | Yes        | Limited*               |
    +---------------+------------+------------+------------------------+
    | ROLLBACK      | N/A        | Yes        | N/A                    |
    +---------------+------------+------------+------------------------+
    | HEALTH_CHECK  | Yes        | Yes        | Yes                    |
    +---------------+------------+------------+------------------------+
    | DESCRIBE      | Yes        | Yes        | Yes                    |
    +---------------+------------+------------+------------------------+
    | CONFIGURE     | Yes        | Yes        | Yes                    |
    +---------------+------------+------------+------------------------+
    | RESET         | Yes        | Yes        | Yes                    |
    +---------------+------------+------------+------------------------+

    *Limited: DRY_RUN for NONDETERMINISTIC handlers may not reflect actual execution.

    Example:
        >>> from omnibase_core.enums import EnumHandlerCommandType
        >>> cmd = EnumHandlerCommandType.EXECUTE
        >>> str(cmd)
        'execute'

        >>> # Exhaustive match with type safety
        >>> def dispatch(cmd: EnumHandlerCommandType) -> str:
        ...     match cmd:
        ...         case EnumHandlerCommandType.EXECUTE:
        ...             return "executing"
        ...         case EnumHandlerCommandType.VALIDATE:
        ...             return "validating"
        ...         case _:
        ...             return "other"
        >>> dispatch(EnumHandlerCommandType.EXECUTE)
        'executing'

    .. versionadded:: 0.4.0
    """

    EXECUTE = "execute"
    """Execute the handler's primary operation."""

    VALIDATE = "validate"
    """Validate input data without executing the operation."""

    DRY_RUN = "dry_run"
    """Simulate execution without performing side effects."""

    ROLLBACK = "rollback"
    """Rollback or undo a previous operation."""

    HEALTH_CHECK = "health_check"
    """Check handler health and availability."""

    DESCRIBE = "describe"
    """Describe handler capabilities and metadata."""

    CONFIGURE = "configure"
    """Configure handler settings or parameters."""

    RESET = "reset"
    """Reset handler state to initial configuration."""

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
        # Lazy import to avoid circular dependency with error_codes
        from omnibase_core.errors import ModelOnexError

        raise ModelOnexError(
            message=f"Unhandled enum value: {value}",
            error_code=EnumCoreErrorCode.INVALID_OPERATION,
        )


__all__ = ["EnumHandlerCommandType"]
