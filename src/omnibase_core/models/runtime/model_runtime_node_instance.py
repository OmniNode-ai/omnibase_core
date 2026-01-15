"""
ModelRuntimeNodeInstance - Lightweight execution wrapper for ONEX nodes.

This module provides the ModelRuntimeNodeInstance class, which serves as a lightweight
wrapper around node execution. It handles lifecycle management (initialize/shutdown)
and envelope reception, delegating actual execution to EnvelopeRouter.

Architecture Pattern - Delegation:
    ModelRuntimeNodeInstance follows the ONEX delegation pattern where the instance itself
    contains NO business logic or I/O operations. All execution is delegated
    to the EnvelopeRouter, which handles:

    - Handler dispatch (routing envelopes to appropriate handlers)
    - Error handling and recovery
    - Observability (logging, metrics, tracing)
    - Transaction management
    - Retry logic and circuit breaking

    This separation ensures:
    1. ModelRuntimeNodeInstance remains a pure coordination layer
    2. Testing is simplified (mock the runtime, test the instance)
    3. Different runtime implementations can be swapped without changing instances
    4. The instance can be serialized/deserialized for distributed scenarios

Why Delegation?
    Direct execution in ModelRuntimeNodeInstance would couple envelope handling to the
    instance lifecycle, making it difficult to:
    - Share execution infrastructure across multiple instances
    - Implement cross-cutting concerns (logging, tracing) consistently
    - Support different execution strategies (sync, async, parallel)
    - Test instance behavior independently of execution behavior

Usage:
    .. code-block:: python

        from omnibase_core.models.runtime import ModelRuntimeNodeInstance
        from omnibase_core.enums import EnumNodeType
        from omnibase_core.models.contracts import ModelContractCompute

        # Create a node instance with its contract
        instance = ModelRuntimeNodeInstance(
            slug="my-compute-node",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            contract=my_contract,
        )

        # Set the runtime (injected, not created by instance)
        instance.set_runtime(runtime)

        # Initialize lifecycle
        await instance.initialize()

        # Handle envelopes (delegates to runtime)
        result = await instance.handle(envelope)

        # Cleanup
        await instance.shutdown()

Thread Safety:
    WARNING: The _runtime and _initialized PrivateAttrs are NOT thread-safe.

    ModelRuntimeNodeInstance uses frozen=True configuration, making the model fields
    (slug, node_type, contract) immutable after creation. However, the private
    attributes (_runtime, _initialized) are mutable and have no synchronization.

    Safe Usage Pattern:
        1. Create the instance (single thread)
        2. Call set_runtime() (single thread)
        3. Call initialize() (single thread)
        4. Share the instance across threads
        5. Call handle() concurrently (thread safety is runtime's responsibility)
        6. Call shutdown() (single thread, after all handle() calls complete)

    The EnvelopeRouter implementation is responsible for thread safety of the
    actual execution within handle(). See CLAUDE.md thread safety matrix.

    Concurrent handle() and shutdown() Behavior:
        If shutdown() is called while handle() operations are in progress:
        1. In-flight handle() calls may complete normally or encounter errors
        2. The _initialized flag is NOT protected by a lock
        3. This is a known limitation - callers are responsible for ensuring
           all handle() calls complete before calling shutdown()
        4. Future versions may add an atomic state transition mechanism

Related:
    - OMN-227: NodeInstance execution wrapper
    - OMN-228: EnvelopeRouter with execute_with_handler
    - OMN-1067: Move RuntimeNodeInstance to models/runtime/
    - ModelOnexEnvelope: The envelope format handled by this instance
    - ModelContractBase: The contract defining node behavior

See Also:
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md
    - docs/guides/node-building/README.md

Future Considerations:
    The current lifecycle uses a simple boolean `_initialized` flag for state
    tracking. Future versions may introduce a state enum for more complex
    lifecycle management:

    - EnumNodeInstanceState.CREATED: Instance created, no runtime set
    - EnumNodeInstanceState.CONFIGURED: Runtime set via set_runtime()
    - EnumNodeInstanceState.INITIALIZING: initialize() in progress
    - EnumNodeInstanceState.READY: Ready to handle envelopes
    - EnumNodeInstanceState.SHUTTING_DOWN: shutdown() in progress
    - EnumNodeInstanceState.SHUTDOWN: Shutdown complete

    This would enable:
    - More granular state queries (is_ready(), is_shutting_down())
    - State transition validation with explicit allowed transitions
    - Better observability and debugging of lifecycle issues
    - Support for async initialization/shutdown with intermediate states

    For now, the boolean approach is sufficient for the current use cases
    and keeps the implementation simple per YAGNI principles.
"""

from __future__ import annotations

__all__ = ["ModelRuntimeNodeInstance", "NodeInstance"]

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.runtime.runtime_protocol_node import ProtocolNodeRuntime


class ModelRuntimeNodeInstance(BaseModel):
    """
    Lightweight execution wrapper for ONEX nodes.

    ModelRuntimeNodeInstance is a thin coordination layer that:
    - Holds node identity (slug, type, contract)
    - Manages lifecycle (initialize, shutdown)
    - Receives envelopes and delegates to runtime

    This class contains NO business logic or I/O operations. All execution
    is delegated to the EnvelopeRouter via execute_with_handler().

    Attributes:
        slug: Unique identifier for this node instance. Used for routing,
            logging, and identification in distributed systems.
        node_type: The ONEX node type classification (COMPUTE, EFFECT,
            REDUCER, ORCHESTRATOR). Determines execution semantics.
        contract: The contract defining this node's behavior, including
            input/output models, performance requirements, and dependencies.

    Example:
        .. code-block:: python

            instance = ModelRuntimeNodeInstance(
                slug="metrics-aggregator",
                node_type=EnumNodeType.REDUCER_GENERIC,
                contract=aggregator_contract,
            )

            # Runtime injection (before use)
            instance.set_runtime(my_runtime)

            # Lifecycle management
            await instance.initialize()

            # Process envelopes
            response = await instance.handle(request_envelope)

            # Cleanup
            await instance.shutdown()

    Thread Safety:
        The model is frozen (immutable) after creation. The runtime
        reference is managed via PrivateAttr and should be set once
        before concurrent access. See module docstring for details.

    See Also:
        - ProtocolNodeRuntime: The protocol implemented by runtime
        - ModelContractBase: The contract type for node configuration
        - ModelOnexEnvelope: The envelope type for input/output
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    slug: str = Field(
        ...,
        description="Unique identifier for this node instance. "
        "Used for routing, logging, and distributed system identification.",
        min_length=1,
        max_length=256,
    )

    node_type: EnumNodeType = Field(
        ...,
        description="ONEX node type classification (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR). "
        "Determines execution semantics and workflow position.",
    )

    contract: ModelContractBase = Field(
        ...,
        description="Contract defining node behavior including input/output models, "
        "performance requirements, validation rules, and dependencies.",
    )

    # Private attribute for runtime reference (not part of the model's data)
    # This allows mutation while keeping the model frozen
    _runtime: ProtocolNodeRuntime | None = PrivateAttr(default=None)

    # Lifecycle state tracking
    _initialized: bool = PrivateAttr(default=False)

    def set_runtime(self, runtime: ProtocolNodeRuntime) -> None:
        """
        Set the runtime for this node instance.

        The runtime handles all actual execution logic. This method should
        be called once during instance setup, before any envelope handling.

        Args:
            runtime: The runtime implementation that will handle envelope
                execution. Must implement ProtocolNodeRuntime.

        Raises:
            ModelOnexError: If runtime is already set (to prevent accidental
                replacement during execution).

        Example:
            .. code-block:: python

                instance = ModelRuntimeNodeInstance(...)
                instance.set_runtime(my_runtime)  # Call once during setup

        Note:
            The runtime is intentionally not a constructor parameter to:
            1. Keep the model's data (slug, type, contract) separate from behavior
            2. Allow serialization/deserialization of instances without runtime
            3. Support dependency injection patterns where runtime is provided later
        """
        if self._runtime is not None:
            raise ModelOnexError(
                message=f"Runtime already set for ModelRuntimeNodeInstance '{self.slug}'. "
                "Cannot replace runtime during execution.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                node_slug=self.slug,
                node_type=self.node_type,
            )
        self._runtime = runtime

    @property
    def runtime(self) -> ProtocolNodeRuntime:
        """
        Get runtime reference with validation (internal API).

        This property provides type-safe access to the runtime, raising a
        descriptive error if the runtime has not been set. Primarily intended
        for internal use within this class (e.g., in handle()).

        Note:
            This is considered internal API. External code should interact
            with the instance through handle(), not by accessing the runtime
            directly. The runtime is an implementation detail that may change.

        Returns:
            ProtocolNodeRuntime: The configured runtime instance.

        Raises:
            ModelOnexError: If runtime has not been set via set_runtime().

        Example:
            .. code-block:: python

                # Internal usage pattern (within this class)
                return await self.runtime.execute_with_handler(envelope, self)
        """
        if self._runtime is None:
            raise ModelOnexError(
                message=f"Runtime not set for ModelRuntimeNodeInstance '{self.slug}'. "
                "Call set_runtime() before accessing runtime.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                node_slug=self.slug,
                node_type=self.node_type,
            )
        return self._runtime

    async def initialize(self) -> None:
        """
        Initialize the node instance for operation.

        This method prepares the instance for envelope handling. It should
        be called once after runtime injection and before handling envelopes.

        The initialization phase:
        1. Validates that runtime is set
        2. Marks the instance as initialized
        3. Future: May perform contract validation, resource allocation, etc.

        Raises:
            ModelOnexError: If runtime is not set before initialization.
            ModelOnexError: If already initialized (idempotency protection).

        Example:
            .. code-block:: python

                instance.set_runtime(runtime)
                await instance.initialize()  # Now ready for handle()

        Note:
            This is an async method to support future initialization steps
            that may require I/O (performed by the runtime, not this class).
        """
        if self._runtime is None:
            raise ModelOnexError(
                message=f"Cannot initialize ModelRuntimeNodeInstance '{self.slug}' without runtime. "
                "Call set_runtime() before initialize().",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                node_slug=self.slug,
                node_type=self.node_type,
            )

        if self._initialized:
            raise ModelOnexError(
                message=f"ModelRuntimeNodeInstance '{self.slug}' is already initialized. "
                "Cannot initialize twice.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                node_slug=self.slug,
                node_type=self.node_type,
            )

        self._initialized = True

    async def shutdown(self) -> None:
        """
        Shutdown the node instance and release resources.

        This method cleanly shuts down the instance, marking it as
        no longer initialized. After shutdown, the instance cannot
        handle envelopes until re-initialized.

        The shutdown phase:
        1. Marks the instance as not initialized
        2. Future: May release resources, close connections, etc.

        Raises:
            ModelOnexError: If not initialized (nothing to shut down).

        Example:
            .. code-block:: python

                await instance.shutdown()
                # Instance can no longer handle envelopes

        Warning:
            This method is NOT thread-safe with respect to concurrent handle()
            calls. Ensure all handle() operations have completed before calling
            shutdown(). Future versions may implement atomic state transitions
            with proper synchronization.

        Note:
            This is an async method to support future shutdown steps
            that may require I/O (performed by the runtime, not this class).
            Shutdown is idempotent in the sense that calling it on an
            uninitialized instance raises an error (explicit failure).
        """
        if not self._initialized:
            raise ModelOnexError(
                message=f"Cannot shutdown ModelRuntimeNodeInstance '{self.slug}' that is not initialized.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                node_slug=self.slug,
                node_type=self.node_type,
            )

        self._initialized = False

    async def handle(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """
        Handle an incoming envelope by delegating to the runtime.

        This is the main entry point for envelope processing. The method:
        1. Validates the instance is ready (initialized with runtime)
        2. Delegates to runtime.execute_with_handler()
        3. Returns the response envelope

        This method contains NO execution logic - it purely delegates.
        All handler dispatch, error handling, observability, and transaction
        management is the responsibility of the runtime.

        Args:
            envelope: The input envelope to process. Contains:
                - operation: The operation type to route to a handler
                - payload: The business data for the handler
                - metadata: Correlation IDs, tracing info, etc.

        Returns:
            ModelOnexEnvelope: The response envelope from execution.
                May be a success response or an error response depending
                on execution outcome.

        Raises:
            ModelOnexError: If instance is not initialized.
            ModelOnexError: If runtime is not set.
            ModelOnexError: If runtime execution fails with unrecoverable error.

        Example:
            .. code-block:: python

                # Create request envelope
                request = ModelOnexEnvelope.create_request(
                    operation="PROCESS_DATA",
                    payload={"data": "value"},
                    source_node="client",
                    target_node=instance.slug,
                )

                # Handle and get response
                response = await instance.handle(request)

                if response.success:
                    result = response.payload
                else:
                    error = response.error

        Note:
            The runtime is responsible for:
            - Routing to the correct handler based on envelope.operation
            - Error handling and recovery
            - Creating appropriate response envelopes
            - Logging and metrics
        """
        if not self._initialized:
            # Safely extract operation for error context (envelope may be None)
            envelope_operation = (
                getattr(envelope, "operation", None) if envelope else None
            )
            raise ModelOnexError(
                message=f"ModelRuntimeNodeInstance '{self.slug}' is not initialized. "
                "Call initialize() before handling envelopes.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                node_slug=self.slug,
                node_type=self.node_type,
                envelope_operation=envelope_operation,
            )

        # Delegate to runtime - all execution happens there
        return await self.runtime.execute_with_handler(envelope, self)

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns:
            str: Format "ModelRuntimeNodeInstance[slug=..., type=..., initialized=...]"
        """
        return (
            f"ModelRuntimeNodeInstance["
            f"slug={self.slug}, "
            f"type={self.node_type}, "
            f"initialized={self._initialized}]"
        )

    def __repr__(self) -> str:
        """
        Detailed representation for debugging.

        Returns:
            str: Detailed format including contract name
        """
        return (
            f"ModelRuntimeNodeInstance("
            f"slug={self.slug!r}, "
            f"node_type={self.node_type!r}, "
            f"contract={self.contract.name!r}, "
            f"initialized={self._initialized})"
        )


# Primary export alias
NodeInstance = ModelRuntimeNodeInstance
