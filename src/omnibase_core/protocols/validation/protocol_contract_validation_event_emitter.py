"""
Protocol for Contract Validation Event Emitter.

This module defines the protocol interface for emitting contract validation
lifecycle events. The emitter provides a simple abstraction over the underlying
event bus for contract validation-specific events.

Location:
    ``omnibase_core.protocols.validation.protocol_contract_validation_event_emitter``

Import Example:
    .. code-block:: python

        from omnibase_core.protocols.validation import (
            ProtocolContractValidationEventEmitter,
        )

Design Notes:
    - **Simple Interface**: Single `emit` method for all contract validation events
    - **Type Safety**: Accepts only ModelContractValidationEventBase subclasses
    - **Async First**: All emission is async for non-blocking event bus integration
    - **Optional Integration**: Pipelines can operate without an emitter (None)

Related:
    - OMN-1151: Event emission integration in ContractValidationPipeline
    - OMN-1146: Contract validation event models

See Also:
    - :class:`ModelContractValidationEventBase`: Base event model
    - :class:`ModelContractValidationStartedEvent`: Validation started event
    - :class:`ModelContractValidationPassedEvent`: Validation passed event
    - :class:`ModelContractValidationFailedEvent`: Validation failed event
    - :class:`ModelContractMergeStartedEvent`: Merge started event
    - :class:`ModelContractMergeCompletedEvent`: Merge completed event

.. versionadded:: 0.4.1
    Initial implementation as part of OMN-1151.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.events.contract_validation import (
        ModelContractValidationEventBase,
    )

__all__ = ["ProtocolContractValidationEventEmitter"]


@runtime_checkable
class ProtocolContractValidationEventEmitter(Protocol):
    """
    Protocol interface for contract validation event emission.

    This protocol provides a simple interface for emitting contract validation
    lifecycle events. Implementations typically wrap an event bus and handle
    serialization and topic routing internally.

    The protocol supports duck typing via @runtime_checkable, allowing any
    object with a compatible `emit` method to be used as an emitter.

    Thread Safety:
        Implementations should be thread-safe for concurrent emit calls.
        The emit method should not block the caller beyond event bus latency.

    Example:
        >>> class MyEventEmitter:
        ...     def __init__(self, event_bus: ProtocolEventBusPublisher):
        ...         self._bus = event_bus
        ...
        ...     async def emit(
        ...         self, event: ModelContractValidationEventBase
        ...     ) -> None:
        ...         payload = event.model_dump_json().encode()
        ...         await self._bus.publish(
        ...             topic="onex.contract.validation",
        ...             key=event.contract_name.encode(),
        ...             value=payload,
        ...         )
        ...
        >>> # Use with pipeline
        >>> pipeline = ContractValidationPipeline(
        ...     event_emitter=MyEventEmitter(event_bus),
        ...     correlation_id=uuid4(),
        ... )

    Note:
        The emitter is optional in the pipeline. When not provided, the pipeline
        operates without event emission, which is suitable for unit tests and
        scenarios where event tracking is not required.

    .. versionadded:: 0.4.1
    """

    async def emit(self, event: ModelContractValidationEventBase) -> None:
        """
        Emit a contract validation lifecycle event.

        This method should serialize the event and publish it to the appropriate
        event bus topic. The method is async to support non-blocking event bus
        integration.

        Args:
            event: The contract validation event to emit. Must be an instance
                of ModelContractValidationEventBase or a subclass (started,
                passed, failed, merge started, merge completed).

        Raises:
            OnexError: If event emission fails due to event bus issues,
                serialization errors, or network problems.

        Example:
            >>> started_event = ModelContractValidationStartedEvent.create(
            ...     contract_name="my-contract",
            ...     run_id=uuid4(),
            ...     context=ModelContractValidationContext(),
            ... )
            >>> await emitter.emit(started_event)
        """
        ...
