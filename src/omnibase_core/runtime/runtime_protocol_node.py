"""
ProtocolNodeRuntime - Protocol for node runtime implementations.

This module defines the protocol interface that EnvelopeRouter implementations
must follow. It enables dependency inversion where NodeInstance depends on
an abstract interface rather than a concrete implementation.

Related:
    - OMN-227: NodeInstance execution wrapper
    - OMN-228: EnvelopeRouter implementation
    - OMN-1067: Move RuntimeNodeInstance to models/runtime/
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
    from omnibase_core.models.runtime.model_runtime_node_instance import (
        ModelRuntimeNodeInstance,
    )


@runtime_checkable
class ProtocolNodeRuntime(Protocol):
    """
    Protocol defining the interface for node runtime implementations.

    This protocol enables dependency inversion - ModelRuntimeNodeInstance depends on
    the abstract ProtocolNodeRuntime interface rather than a concrete
    EnvelopeRouter implementation. This allows:

    - Different runtime implementations (sync, async, distributed)
    - Easy mocking in tests
    - Future extensibility without changing ModelRuntimeNodeInstance

    The runtime is responsible for all actual execution, including:
    - Handler dispatch and invocation
    - Error handling and recovery
    - Observability (logging, metrics, tracing)
    - Transaction management

    Note:
        This protocol is implemented by EnvelopeRouter (OMN-228).
        It defines the contract that ModelRuntimeNodeInstance depends on.

    Design Decision (Type Variance):
        The `instance` parameter uses the concrete `ModelRuntimeNodeInstance` type rather
        than a generic TypeVar or Protocol. This is intentional per YAGNI - we only
        have one NodeInstance implementation. If multiple instance types are needed
        in the future, this can be generalized to a TypeVar or NodeInstanceProtocol.
        See PR #141 review discussion.
    """

    async def execute_with_handler(
        self,
        envelope: ModelOnexEnvelope,
        instance: ModelRuntimeNodeInstance,
    ) -> ModelOnexEnvelope:
        """
        Execute the node's handler for the given envelope.

        This method is called by ModelRuntimeNodeInstance.handle() to delegate
        actual execution to the runtime. The runtime is responsible for:

        1. Resolving the appropriate handler based on envelope operation
        2. Invoking the handler with proper context
        3. Handling errors and generating error response envelopes
        4. Recording metrics and traces
        5. Managing transactions if applicable

        Args:
            envelope: The input envelope to process. Contains the operation
                type, payload, and metadata for routing and execution.
            instance: The ModelRuntimeNodeInstance that received this envelope.
                Provides access to the node's contract and configuration.

        Returns:
            ModelOnexEnvelope: The response envelope containing the result
                of execution. May be a success response with payload or
                an error response with error details.

        Raises:
            ModelOnexError: If execution fails and cannot be handled by
                the runtime's error recovery mechanisms.
        """
        ...


__all__ = ["ProtocolNodeRuntime"]
