"""
Protocol for contract validation event emission.

This module provides the protocol definition for emitting contract validation
lifecycle events. It follows the Interface Segregation Principle (ISP) by
providing a minimal interface for event emission.

Location:
    ``omnibase_core.protocols.protocol_contract_validation_event_emitter``

Import Example:
    .. code-block:: python

        from omnibase_core.protocols import ProtocolContractValidationEventEmitter

Design Principles:
    - **ISP Compliant**: Minimal interface for event emission only
    - **Runtime Checkable**: Supports duck typing with @runtime_checkable
    - **Type Safe**: Full type hints for mypy strict mode

See Also:
    - :mod:`omnibase_core.models.events.contract_validation`: Event models
    - :class:`ContractMergeEngine`: Uses this protocol for merge events

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1151 event emission integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.events.contract_validation.model_contract_merge_completed_event import (
        ModelContractMergeCompletedEvent,
    )
    from omnibase_core.models.events.contract_validation.model_contract_merge_started_event import (
        ModelContractMergeStartedEvent,
    )
    from omnibase_core.models.events.contract_validation.model_contract_validation_failed_event import (
        ModelContractValidationFailedEvent,
    )
    from omnibase_core.models.events.contract_validation.model_contract_validation_passed_event import (
        ModelContractValidationPassedEvent,
    )
    from omnibase_core.models.events.contract_validation.model_contract_validation_started_event import (
        ModelContractValidationStartedEvent,
    )

__all__ = ["ProtocolContractValidationEventEmitter"]


@runtime_checkable
class ProtocolContractValidationEventEmitter(Protocol):
    """
    Protocol for emitting contract validation lifecycle events.

    This protocol defines the interface for emitting events during contract
    validation and merge operations. Implementations can emit events to
    various backends (event bus, logging, metrics, etc.).

    The protocol follows ISP - components that only need event emission
    don't need to implement full event bus functionality.

    Methods:
        emit_validation_started: Emit when validation begins
        emit_validation_passed: Emit when validation succeeds
        emit_validation_failed: Emit when validation fails
        emit_merge_started: Emit when merge operation begins
        emit_merge_completed: Emit when merge operation completes

    Example:
        >>> class MyEmitter:
        ...     def emit_merge_started(
        ...         self, event: ModelContractMergeStartedEvent
        ...     ) -> None:
        ...         # Emit to event bus, log, etc.
        ...         pass
        ...
        ...     def emit_merge_completed(
        ...         self, event: ModelContractMergeCompletedEvent
        ...     ) -> None:
        ...         pass
        ...
        >>> emitter: ProtocolContractValidationEventEmitter = MyEmitter()

    Thread Safety:
        Implementations should be thread-safe if used in concurrent contexts.

    .. versionadded:: 0.4.0
    """

    def emit_validation_started(
        self, event: ModelContractValidationStartedEvent
    ) -> None:
        """
        Emit a validation started event.

        Args:
            event: The validation started event to emit.
        """
        ...

    def emit_validation_passed(self, event: ModelContractValidationPassedEvent) -> None:
        """
        Emit a validation passed event.

        Args:
            event: The validation passed event to emit.
        """
        ...

    def emit_validation_failed(self, event: ModelContractValidationFailedEvent) -> None:
        """
        Emit a validation failed event.

        Args:
            event: The validation failed event to emit.
        """
        ...

    def emit_merge_started(self, event: ModelContractMergeStartedEvent) -> None:
        """
        Emit a merge started event.

        Called when a contract merge operation begins.

        Args:
            event: The merge started event to emit.
        """
        ...

    def emit_merge_completed(self, event: ModelContractMergeCompletedEvent) -> None:
        """
        Emit a merge completed event.

        Called when a contract merge operation completes successfully.

        Args:
            event: The merge completed event to emit.
        """
        ...
