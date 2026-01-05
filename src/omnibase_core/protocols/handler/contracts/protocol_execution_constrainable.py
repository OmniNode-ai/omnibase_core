"""
Protocol for objects that can declare execution constraints.

Domain: Execution constraint declaration for handlers and contracts.

This module defines a mixin-style protocol for objects that can declare
execution constraints such as timeouts, retry limits, and resource limits.
Handlers, contracts, and other runtime objects can implement this protocol
to declare their execution requirements.

See Also:
    - ProtocolExecutionConstraints: The constraints definition protocol
    - ProtocolHandlerContract: Contract interface that uses this protocol
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.handler.contracts.protocol_execution_constraints import (
        ProtocolExecutionConstraints,
    )


@runtime_checkable
class ProtocolExecutionConstrainable(Protocol):
    """
    Protocol for objects that can declare execution constraints.

    This is a mixin-style protocol that can be implemented by handlers,
    contracts, or other objects that need to declare execution constraints
    such as timeouts, retry limits, and resource limits.

    Execution constraints allow the runtime to enforce limits on handler
    execution, preventing resource exhaustion and ensuring predictable
    behavior. When constraints are not defined (None), the runtime applies
    default constraints appropriate for the execution context.

    This protocol enables:
        - Timeout enforcement for long-running operations
        - Retry limit specification for transient failures
        - Resource limit declaration for memory/CPU bounds
        - Constraint introspection for monitoring and debugging

    Consistency Invariant:
        Implementations MUST maintain consistency between ``has_constraints()``
        and ``execution_constraints``. Specifically:

        - ``has_constraints()`` MUST return ``True`` if and only if
          ``execution_constraints`` returns a non-None value.
        - ``has_constraints()`` MUST return ``False`` if and only if
          ``execution_constraints`` returns ``None``.

        **Recommended Implementation Pattern**: To guarantee consistency,
        implementers SHOULD derive ``has_constraints()`` directly from
        ``execution_constraints``:

        ```python
        def has_constraints(self) -> bool:
            return self.execution_constraints is not None
        ```

        This pattern ensures the invariant cannot be violated, as the
        boolean result is always derived from the same source of truth.

        **Validation for Implementers**: When testing implementations,
        verify both directions of the invariant:

        ```python
        # Test 1: has_constraints() True implies non-None constraints
        if obj.has_constraints():
            assert obj.execution_constraints is not None

        # Test 2: has_constraints() False implies None constraints
        if not obj.has_constraints():
            assert obj.execution_constraints is None
        ```

    Example:
        Basic usage with constraint checking:

        ```python
        class MyHandler:
            '''Handler with execution constraints.'''

            def __init__(self) -> None:
                self._constraints: ProtocolExecutionConstraints | None = None

            @property
            def execution_constraints(self) -> ProtocolExecutionConstraints | None:
                return self._constraints

            def has_constraints(self) -> bool:
                return self._constraints is not None

        handler = MyHandler()
        assert isinstance(handler, ProtocolExecutionConstrainable)

        if handler.has_constraints():
            constraints = handler.execution_constraints
            print(f"Timeout: {constraints.timeout_seconds}s")
        ```

        Recommended implementation maintaining consistency:

        ```python
        class ConsistentConstrainable:
            '''Implementation with guaranteed consistency.'''

            def __init__(
                self, constraints: ProtocolExecutionConstraints | None = None
            ) -> None:
                self._constraints = constraints

            @property
            def execution_constraints(self) -> ProtocolExecutionConstraints | None:
                return self._constraints

            def has_constraints(self) -> bool:
                # Derived from execution_constraints to ensure consistency.
                # This guarantees the invariant: has_constraints() returns True
                # if and only if execution_constraints returns non-None.
                return self._constraints is not None
        ```

    See Also:
        ProtocolExecutionConstraints: The constraints definition protocol.
        ProtocolHandlerContract: Contract interface that uses this protocol.
    """

    @property
    def execution_constraints(self) -> ProtocolExecutionConstraints | None:
        """
        Get the execution constraints for this object.

        Execution constraints define limits and requirements for how this
        object should be executed by the runtime. Common constraints include:
            - Timeout limits (maximum execution time)
            - Retry policies (max attempts, backoff strategy)
            - Resource limits (memory, CPU, connections)
            - Concurrency limits (max parallel executions)

        Returns:
            Execution constraints if defined, None otherwise.
            When None, default constraints should be applied by the runtime.
            The runtime determines appropriate defaults based on the
            execution context and system configuration.

        Note:
            Implementations SHOULD return the same instance on repeated
            calls unless the constraints have been explicitly modified.
            Callers SHOULD treat the returned constraints as read-only.
        """
        ...

    def has_constraints(self) -> bool:
        """
        Check if this object has execution constraints defined.

        This method provides a fast check for constraint presence without
        requiring the caller to handle None values. It enables efficient
        conditional logic in the runtime:

        Example:
            ```python
            if constrainable.has_constraints():
                # Apply custom constraints
                apply_constraints(constrainable.execution_constraints)
            else:
                # Apply default constraints
                apply_default_constraints()
            ```

        Returns:
            True if constraints are defined, False otherwise.
            Returns True if and only if ``execution_constraints`` would
            return a non-None value.

        Important:
            This is a **derived property** that MUST be consistent with
            ``execution_constraints``. The consistency invariant requires:

            - Return ``True`` if and only if ``execution_constraints`` is not None
            - Return ``False`` if and only if ``execution_constraints`` is None

            **Recommended Implementation**: Derive directly from the constraints
            property to guarantee consistency:

            ```python
            def has_constraints(self) -> bool:
                return self.execution_constraints is not None
            ```

            Do NOT cache or independently track the boolean state, as this
            can lead to inconsistency if the underlying constraints change.

        See Also:
            The class-level "Consistency Invariant" section for full details.
        """
        ...


__all__ = ["ProtocolExecutionConstrainable"]
