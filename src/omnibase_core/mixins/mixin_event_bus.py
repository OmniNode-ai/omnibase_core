"""
Unified Event Bus Mixin for ONEX Nodes (Publish-Only)

Provides event publishing capabilities including:
- Event completion publishing
- Protocol-based polymorphism
- ONEX standards compliance
- Error handling and logging

This mixin uses composition with ModelEventBusRuntimeState for state management,
avoiding BaseModel inheritance to prevent MRO conflicts in multi-inheritance scenarios.

Thread Safety:
    This mixin provides thread-safe dispose() operations.
    The internal _mixin_lock protects concurrent access to mutable state
    including bindings. Multiple threads can safely call
    dispose_event_bus_resources() concurrently.

    However, bind_*() methods are NOT thread-safe and should only be called
    during initialization before the mixin is shared across threads.

    Lock Hierarchy:
        - ``_class_init_lock`` (class-level): Protects lazy initialization of
          instance locks. Acquired only during first access to _mixin_lock.
        - ``_mixin_lock`` (instance-level): Protects mixin state mutations.
          Acquired during dispose() and state-modifying operations.

        Never acquire _class_init_lock while holding _mixin_lock to avoid
        deadlocks.

    Runtime Misuse Detection:
        The mixin tracks when it transitions to "in use" state via a
        _binding_locked flag. This flag is set to True when:
        - publish_event() or publish_completion_event() operations occur

        If bind_*() methods are called after the flag is set, a ModelOnexError
        is raised (fail-fast behavior). This prevents thread-unsafe binding
        patterns from causing subtle race conditions in production.

Note:
    Listener/consumer functionality has been removed from this mixin.
    Use EventBusSubcontractWiring in omnibase_infra for Kafka consumer
    lifecycle management.
"""

import threading
import uuid
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Generic,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)
from uuid import UUID


@runtime_checkable
class ProtocolEventBusDuckTyped(Protocol):
    """Protocol for duck-typed event bus method access.

    This protocol defines the interface for event bus operations that may not be
    present on all event bus implementations. It is used with cast() to provide
    type-safe access to optional methods while maintaining compatibility with
    legacy event bus implementations.

    The protocol is runtime_checkable to support hasattr() checks before method calls.
    """

    def publish(self, event: object) -> None:
        """Synchronous publish method."""
        ...

    async def publish_async(self, envelope: object) -> None:
        """Asynchronous publish method."""
        ...


# Generic type parameters for typed event processing
InputStateT = TypeVar("InputStateT")
OutputStateT = TypeVar("OutputStateT")

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_topic_naming import (
    validate_message_topic_alignment,
)
from omnibase_core.models.mixins.model_completion_data import ModelCompletionData
from omnibase_core.models.mixins.model_log_data import ModelLogData
from omnibase_core.protocols import ProtocolEventEnvelope
from omnibase_core.protocols.event_bus import (
    ProtocolEventBus,
    ProtocolEventBusRegistry,
)

if TYPE_CHECKING:
    from omnibase_core.models.event_bus import (
        ModelEventBusRuntimeState,
    )


class MixinEventBus(Generic[InputStateT, OutputStateT]):
    """
    Unified mixin for event bus publishing operations in ONEX nodes.

    Provides:
    - Completion event publishing with proper protocols
    - ONEX standards compliance (no dictionaries, proper models)
    - Protocol-based polymorphism for event bus access
    - Error handling and structured logging
    - Type-safe event processing via generic type parameters

    Design:
    - NO BaseModel inheritance (avoids MRO conflicts)
    - Explicit binding REQUIRED in __init__ before any operations
    - Composition with ModelEventBusRuntimeState
    - Generic[InputStateT, OutputStateT] for type-safe event processing

    Initialization Requirement:
        Subclasses MUST call one or more bind_*() methods in their __init__
        before using any event bus operations. Accessing runtime state before
        binding will raise ModelOnexError with instructions to bind first.

        Example:
            >>> class MyNode(MixinEventBus[MyInput, MyOutput]):
            ...     def __init__(self, event_bus: ProtocolEventBus):
            ...         super().__init__()
            ...         self.bind_event_bus(event_bus)  # REQUIRED
            ...         self.bind_node_name("MyNode")   # Optional but recommended

    Validation:
        All bind methods enforce strict validation:
        - bind_node_name(): Rejects empty or whitespace-only strings (raises ModelOnexError)
        - bind_event_bus(): Stores the event bus reference and sets is_bound=True
        - bind_registry(): Stores the registry and sets is_bound=True if registry.event_bus is available

        If no node_name is bound, get_node_name() falls back to class name.

    Reset vs Bind Behavior:
        - **bind_*() methods**: Set configuration values during initialization. These validate
          input and raise ModelOnexError for invalid values. Use in __init__ before the
          instance is shared across threads.
        - **_event_bus_runtime_state.reset()**: Clears the is_bound flag while preserving
          node_name. Use for cleanup between operations (e.g., test teardown)
          or before rebinding with new configuration.
        - **dispose_event_bus_resources()**: Full cleanup that clears all bindings
          and resets runtime state. Use on shutdown.

    Type Parameters:
        InputStateT: The type of input state for event processing
        OutputStateT: The type of output state returned from processing

    Usage:
        class MyNode(MixinEventBus[MyInputState, MyOutputState], SomeOtherBase):
            def __init__(self, event_bus: ProtocolEventBus):
                super().__init__()
                self.bind_event_bus(event_bus)

            def process(self, input_state: MyInputState) -> MyOutputState:
                # Type-safe processing
                return MyOutputState(...)

    Thread Safety:
        - bind_*() methods: MUST be called in __init__ before sharing across threads
        - publish_*(), dispose_*(): Safe for concurrent access after binding
        - Internal state protected by _mixin_lock (lazily initialized via class-level lock)

        See module docstring for detailed lock hierarchy documentation.

    Strict Binding Mode:
        By default (STRICT_BINDING_MODE=True), calling bind_*() methods after the mixin
        is "in use" (i.e., after publish operations) raises ModelOnexError with
        error_code=INVALID_STATE. This fail-fast behavior prevents subtle race
        conditions from reaching production.

        For gradual migration or compatibility with legacy code, disable strict mode:

            class MyLegacyNode(MixinEventBus[InputT, OutputT]):
                STRICT_BINDING_MODE: ClassVar[bool] = False

        When STRICT_BINDING_MODE is False, bind_*() calls after the mixin is in use will
        emit a WARNING log instead of raising an error.

        The default strict mode is recommended for:
        - Production systems where thread-unsafe patterns must be hard failures
        - CI/CD pipelines where errors are caught but warnings might be missed
        - New code where you want to enforce correct patterns from the start

    Note:
        Listener/consumer functionality has been removed from this mixin.
        Use EventBusSubcontractWiring in omnibase_infra for Kafka consumer
        lifecycle management.
    """

    # Class-level lock for thread-safe lazy initialization of instance locks.
    # This prevents the TOCTOU race condition that would occur with a simple
    # dict.setdefault() approach during concurrent first access to _mixin_lock.
    # Using a class-level lock ensures that only one thread at a time can
    # initialize any instance's lock, providing portable thread safety across
    # all Python implementations (CPython, PyPy, Jython, etc.) and future
    # free-threaded Python builds (PEP 703).
    _class_init_lock: threading.Lock = threading.Lock()

    # Strict binding mode flag. When True (the default), bind_*() calls after
    # the mixin is "in use" (after publish operations) will raise ModelOnexError
    # instead of just emitting a warning. Override in subclasses to disable
    # strict enforcement for legacy compatibility.
    #
    # Example (to disable strict mode for legacy code):
    #     class MyLegacyNode(MixinEventBus[InputT, OutputT]):
    #         STRICT_BINDING_MODE: ClassVar[bool] = False
    STRICT_BINDING_MODE: ClassVar[bool] = True

    # --- Lazy State Accessors (avoid MRO hazards) ---

    @property
    def _mixin_lock(self) -> threading.Lock:
        """Lazy accessor for the mixin's internal lock.

        This lock protects concurrent access to mutable state during
        dispose operations. It is created lazily on first access
        to avoid __init__ requirements in the mixin.

        Thread Safety:
            This implementation uses double-checked locking with a class-level
            lock to ensure thread-safe lazy initialization across all Python
            implementations. The pattern works as follows:

            1. **First check (no lock)**: If the lock already exists in __dict__,
               return it immediately. This is the fast path for subsequent accesses.

            2. **Class lock acquisition**: If the lock doesn't exist, acquire the
               class-level _class_init_lock to serialize initialization.

            3. **Second check (under lock)**: Re-check if the lock exists. Another
               thread may have initialized it while we were waiting for the class
               lock.

            4. **Initialization (under lock)**: If still not present, create the
               instance lock and store it in __dict__.

            This pattern is safe across all Python implementations:

            - **CPython**: Works with and without the GIL
            - **PyPy**: Uses the class lock, not GIL atomicity assumptions
            - **Jython/IronPython**: Uses explicit locking, not GIL
            - **Python 3.13+ Free-Threading (PEP 703)**: Uses explicit locking

        Lock Hierarchy:
            - ``_class_init_lock`` (class-level): Protects instance lock creation
            - ``_mixin_lock`` (instance-level): Protects mixin state

            Always acquire _class_init_lock before creating _mixin_lock.
            Never acquire _class_init_lock while holding _mixin_lock.

        Returns:
            A threading.Lock instance unique to this mixin instance.
        """
        attr_name = "_mixin_event_bus_lock"

        # Fast path: lock already exists (no locking needed for read)
        lock = self.__dict__.get(attr_name)
        if lock is not None:
            return cast(threading.Lock, lock)

        # Slow path: need to initialize under class lock
        with MixinEventBus._class_init_lock:
            # Double-check after acquiring lock (another thread may have initialized)
            lock = self.__dict__.get(attr_name)
            if lock is not None:
                return cast(threading.Lock, lock)

            # Create and store the instance lock
            new_lock = threading.Lock()
            self.__dict__[attr_name] = new_lock
            return new_lock

    @property
    def _event_bus_runtime_state(self) -> "ModelEventBusRuntimeState":
        """Accessor for runtime state - requires explicit binding via bind_*() methods.

        Returns:
            The ModelEventBusRuntimeState instance set by bind_*() methods.

        Raises:
            ModelOnexError: If accessed before calling a bind_*() method in __init__.
                This ensures explicit initialization is required and prevents
                silent lazy initialization that could mask programming errors.
        """
        try:
            return cast(
                "ModelEventBusRuntimeState",
                object.__getattribute__(self, "_mixin_event_bus_state"),
            )
        except AttributeError:
            raise ModelOnexError(
                message=f"Event bus runtime state not initialized on {self.__class__.__name__}. "
                "Call bind_event_bus() or bind_registry() in __init__ before using the mixin.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={
                    "class_name": self.__class__.__name__,
                    "hint": "Add 'self.bind_event_bus(event_bus)' to your __init__ method",
                },
            ) from None

    def _ensure_runtime_state(self) -> "ModelEventBusRuntimeState":
        """Ensure runtime state exists, creating it if necessary.

        This method is used by bind_*() methods to initialize the runtime state
        on first binding. Unlike _event_bus_runtime_state property which raises
        an error for uninitialized state, this method creates the state if needed.

        Returns:
            The ModelEventBusRuntimeState instance (existing or newly created).

        Note:
            This is the ONLY place where lazy state creation should occur.
            All bind_*() methods should use this method to access state.
        """
        try:
            return cast(
                "ModelEventBusRuntimeState",
                object.__getattribute__(self, "_mixin_event_bus_state"),
            )
        except AttributeError:
            from omnibase_core.models.event_bus import ModelEventBusRuntimeState

            state = ModelEventBusRuntimeState.create_unbound()
            object.__setattr__(self, "_mixin_event_bus_state", state)
            return state

    # --- Binding Lock for Thread Safety Detection ---

    def _is_binding_locked(self) -> bool:
        """Check if the mixin has transitioned to 'in use' state.

        Returns True if bind_*() methods should no longer be called
        because the mixin is being used by threads (publish operations
        have occurred).

        Returns:
            True if binding is locked, False otherwise.
        """
        return getattr(self, "_mixin_binding_locked", False)

    def _lock_binding(self) -> None:
        """Mark the mixin as 'in use', locking further bind_*() calls.

        After this method is called, any subsequent bind_*() calls will
        raise ModelOnexError (if STRICT_BINDING_MODE is True, the default)
        or emit a WARNING to alert developers of potential thread-safety issues.

        This is called automatically when:
        - publish_event() or publish_completion_event() performs publishing

        Thread Safety:
            This method is thread-safe - the flag is set atomically under
            the mixin lock to prevent race conditions between check and bind.
        """
        with self._mixin_lock:
            object.__setattr__(self, "_mixin_binding_locked", True)

    def _warn_if_binding_locked(self, method_name: str) -> None:
        """Emit a warning or raise an error if bind_*() is called after mixin is in use.

        .. deprecated::
            This method is deprecated and will be removed in v1.0.
            The check-and-bind logic is now inlined into bind_*() methods
            and executed atomically under the mixin lock to prevent race conditions.

        This method implements runtime misuse detection for thread-unsafe
        binding patterns. The behavior depends on the STRICT_BINDING_MODE class variable:

        - STRICT_BINDING_MODE = True (default): Raises ModelOnexError with INVALID_STATE.
          This is the recommended mode for production to catch misuse early.

        - STRICT_BINDING_MODE = False: Emits a structured WARNING log.
          Use this for gradual migration or compatibility with legacy code.

        Args:
            method_name: The name of the bind method being called
                (e.g., "bind_event_bus", "bind_registry").

        Raises:
            ModelOnexError: If STRICT_BINDING_MODE is True and the mixin is already
                in use (binding is locked). Error code is INVALID_STATE.

        Thread Safety:
            This method MUST only be called while holding self._mixin_lock.
            The bind_*() methods now inline this logic to ensure atomic
            check-and-bind operations, eliminating the previous race condition.

        Note:
            The warning/error includes the method name and node name for easy
            identification of problematic code paths in logs.

        Example:
            To disable strict mode (allow warn-only), subclass and override:

                class MyLegacyNode(MixinEventBus[InputT, OutputT]):
                    STRICT_BINDING_MODE: ClassVar[bool] = False

            Now bind_*() calls after publish will warn.
        """
        if self._is_binding_locked():
            message = (
                f"MIXIN_BIND: {method_name}() called after mixin is in use. "
                "bind_*() methods should be called in __init__ before sharing across threads."
            )

            if self.STRICT_BINDING_MODE:
                raise ModelOnexError(
                    message=message,
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                    context={
                        "method_name": method_name,
                        "node_name": self.get_node_name(),
                        "class_name": self.__class__.__name__,
                    },
                )

            emit_log_event(
                LogLevel.WARNING,
                message,
                ModelLogData(node_name=self.get_node_name()),
            )

    # --- Explicit Binding Methods ---

    def bind_event_bus(self, event_bus: ProtocolEventBus) -> None:
        """Explicitly bind an event bus instance to this mixin.

        This method must be called before any event publishing operations.
        The event bus is stored as a private attribute and used for all
        subsequent publish operations.

        Thread Safety:
            This method uses atomic check-and-bind under the mixin lock.
            It should only be called during __init__ before the mixin
            instance is shared across threads. If called after the mixin
            is in use (after publish operations), a ModelOnexError is raised
            (STRICT_BINDING_MODE=True, default) or a WARNING is emitted
            (STRICT_BINDING_MODE=False).

        Args:
            event_bus: The event bus instance implementing ProtocolEventBus.
                Must support publish() or publish_async() methods.

        Raises:
            ModelOnexError: If STRICT_BINDING_MODE is True and the mixin is
                already in use (binding is locked). Error code is INVALID_STATE.

        Note:
            After binding, is_bound flag is set to True on the runtime state.
            Use _has_event_bus() to check if binding was successful.

        Example:
            >>> node = MyNode()
            >>> node.bind_event_bus(event_bus)
            >>> node.publish_completion_event("complete", data)  # Now works
        """
        # Ensure runtime state exists BEFORE acquiring lock
        # (state creation doesn't need lock protection)
        state = self._ensure_runtime_state()

        # Atomic check-and-bind under lock to prevent race conditions
        with self._mixin_lock:
            if self._is_binding_locked():
                message = (
                    "MIXIN_BIND: bind_event_bus() called after mixin is in use. "
                    "bind_*() methods should be called in __init__ before sharing across threads."
                )
                if self.STRICT_BINDING_MODE:
                    raise ModelOnexError(
                        message=message,
                        error_code=EnumCoreErrorCode.INVALID_STATE,
                        context={
                            "method_name": "bind_event_bus",
                            "node_name": self.get_node_name(),
                            "class_name": self.__class__.__name__,
                        },
                    )
                emit_log_event(
                    LogLevel.WARNING,
                    message,
                    ModelLogData(node_name=self.get_node_name()),
                )
            object.__setattr__(self, "_bound_event_bus", event_bus)
            state.is_bound = True

        # Log outside lock (avoid holding locks during I/O)
        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_BIND: Event bus bound to mixin",
            ModelLogData(node_name=self.get_node_name()),
        )

    def bind_registry(self, registry: ProtocolEventBusRegistry) -> None:
        """Bind a registry that provides event bus access.

        Alternative to bind_event_bus() for cases where the event bus is
        accessed through a registry pattern. The registry's event_bus property
        will be used for all publishing operations.

        Thread Safety:
            This method uses atomic check-and-bind under the mixin lock.
            It should only be called during __init__ before the mixin
            instance is shared across threads. If called after the mixin
            is in use (after publish operations), a ModelOnexError is raised
            (STRICT_BINDING_MODE=True, default) or a WARNING is emitted
            (STRICT_BINDING_MODE=False).

        Args:
            registry: A registry implementing ProtocolEventBusRegistry.
                Must have an event_bus property that returns ProtocolEventBus.

        Raises:
            ModelOnexError: If STRICT_BINDING_MODE is True and the mixin is
                already in use (binding is locked). Error code is INVALID_STATE.

        Note:
            If registry.event_bus is not None, is_bound flag is set to True.
            The registry is stored and its event_bus is resolved on each publish.

        Example:
            >>> node = MyNode()
            >>> node.bind_registry(my_registry)
            >>> # Event bus is accessed via registry.event_bus
        """
        # Ensure runtime state exists BEFORE acquiring lock
        # (state creation doesn't need lock protection)
        state = self._ensure_runtime_state()

        # Atomic check-and-bind under lock to prevent race conditions
        with self._mixin_lock:
            if self._is_binding_locked():
                message = (
                    "MIXIN_BIND: bind_registry() called after mixin is in use. "
                    "bind_*() methods should be called in __init__ before sharing across threads."
                )
                if self.STRICT_BINDING_MODE:
                    raise ModelOnexError(
                        message=message,
                        error_code=EnumCoreErrorCode.INVALID_STATE,
                        context={
                            "method_name": "bind_registry",
                            "node_name": self.get_node_name(),
                            "class_name": self.__class__.__name__,
                        },
                    )
                emit_log_event(
                    LogLevel.WARNING,
                    message,
                    ModelLogData(node_name=self.get_node_name()),
                )
            object.__setattr__(self, "_bound_registry", registry)
            if registry.event_bus is not None:
                state.is_bound = True

        # Log outside lock (avoid holding locks during I/O)
        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_BIND: Registry bound to mixin",
            ModelLogData(node_name=self.get_node_name()),
        )

    def bind_node_name(self, node_name: str) -> None:
        """Bind the node name used for event publishing and logging.

        The node name is included in published events and log messages
        for identification and tracing purposes. If not bound, the
        class name is used as a fallback.

        Thread Safety:
            This method uses atomic check-and-bind under the mixin lock.
            It should only be called during __init__ before the mixin
            instance is shared across threads. If called after the mixin
            is in use (after publish operations), a ModelOnexError is raised
            (STRICT_BINDING_MODE=True, default) or a WARNING is emitted
            (STRICT_BINDING_MODE=False).

        Args:
            node_name: The human-readable name of this node. Must be a
                non-empty string. Should be unique within the system for
                proper event correlation.

        Raises:
            ModelOnexError: If node_name is empty or whitespace-only.
            ModelOnexError: If STRICT_BINDING_MODE is True and the mixin is
                already in use (binding is locked). Error code is INVALID_STATE.

        Note:
            This affects get_node_name() return value and all log output.
            If no node name is bound (state.node_name is None), the
            get_node_name() method returns the class name as a fallback.

        Validation:
            This method validates that node_name is non-empty and non-whitespace,
            consistent with ModelEventBusRuntimeState.bind() validation. To clear
            the node name binding, use _event_bus_runtime_state.reset() followed
            by re-binding with the desired configuration.
        """
        # Validate node_name BEFORE acquiring lock (fail-fast validation)
        if not node_name or not node_name.strip():
            raise ModelOnexError(
                message="node_name must be a non-empty string for binding; "
                "use _event_bus_runtime_state.reset() to unbind without clearing configuration",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                context={
                    "class_name": self.__class__.__name__,
                    "provided_value": repr(node_name),
                },
            )

        # Ensure runtime state exists BEFORE acquiring lock
        # (state creation doesn't need lock protection)
        state = self._ensure_runtime_state()

        # Atomic check-and-bind under lock to prevent race conditions
        with self._mixin_lock:
            if self._is_binding_locked():
                message = (
                    "MIXIN_BIND: bind_node_name() called after mixin is in use. "
                    "bind_*() methods should be called in __init__ before sharing across threads."
                )
                if self.STRICT_BINDING_MODE:
                    raise ModelOnexError(
                        message=message,
                        error_code=EnumCoreErrorCode.INVALID_STATE,
                        context={
                            "method_name": "bind_node_name",
                            "node_name": self.get_node_name(),
                            "class_name": self.__class__.__name__,
                        },
                    )
                emit_log_event(
                    LogLevel.WARNING,
                    message,
                    ModelLogData(node_name=self.get_node_name()),
                )
            state.node_name = node_name

    # --- Fail-Fast Event Bus Access ---

    def _require_event_bus(self) -> ProtocolEventBus:
        """Get event bus or raise ModelOnexError if not bound.

        Returns:
            The bound event bus instance.

        Raises:
            ModelOnexError: If no event bus is bound.
        """
        bus = self._get_event_bus()
        if bus is None:
            raise ModelOnexError(
                message=f"Event bus not bound on {self.__class__.__name__}. "
                "Call bind_event_bus() or bind_registry() before publishing.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={"class_name": self.__class__.__name__},
            )
        return bus

    def _get_event_bus(self) -> ProtocolEventBus | None:
        """
        Resolve event bus using protocol-based polymorphism.

        Explicit binding is required before this method returns a valid event bus.
        Call bind_event_bus() or bind_registry() in __init__ before using.

        Returns:
            The event bus instance or None if not bound.
        """
        # Try direct event_bus binding first
        try:
            bus = object.__getattribute__(self, "_bound_event_bus")
            if bus is not None:
                return cast(ProtocolEventBus, bus)
        except AttributeError:
            pass  # Not bound via bind_event_bus()

        # Try registry binding
        try:
            registry = object.__getattribute__(self, "_bound_registry")
            # Access event_bus property on registry - registry must conform to protocol
            event_bus = registry.event_bus
            if event_bus is not None:
                return cast(ProtocolEventBus, event_bus)
        except AttributeError:
            pass  # Not bound via bind_registry()

        return None

    def _has_event_bus(self) -> bool:
        """Check if an event bus is currently available for publishing.

        Use this method to check availability before attempting operations that
        require an event bus. This is useful for optional event publishing where
        you want to gracefully skip rather than raise an error.

        For operations that require an event bus, prefer _require_event_bus()
        which will raise ModelOnexError with a descriptive message.

        Returns:
            True if an event bus is bound and available, False otherwise.

        Example:
            >>> if self._has_event_bus():
            ...     self.publish_completion_event("done", data)
            ... else:
            ...     self._log_warn("Skipping event - no bus", "publish")
        """
        return self._get_event_bus() is not None

    # --- Node Interface Methods (to be overridden by subclasses) ---

    def get_node_name(self) -> str:
        """Get the name of this node for event publishing and logging.

        Returns the bound node name if set via bind_node_name(), otherwise
        falls back to the class name. The node name is used in event
        correlation and logging context.

        Returns:
            The node name string. Either the explicitly bound name or
            the class name as a fallback.

        Note:
            This method is safe to call before bind_*() methods - it will
            return the class name if runtime state has not been initialized.
        """
        # Safe access to state - return class name fallback if state doesn't exist
        try:
            state = cast(
                "ModelEventBusRuntimeState",
                object.__getattribute__(self, "_mixin_event_bus_state"),
            )
            if state.node_name:
                return state.node_name
        except AttributeError:
            # State not initialized yet - use class name fallback
            pass
        return self.__class__.__name__

    def get_node_id(self) -> UUID:
        """Get the unique identifier for this node.

        Returns the node's UUID for event attribution. If a _node_id
        attribute exists on the instance, that value is returned.
        Otherwise, generates a deterministic UUID v5 from the node name
        using the DNS namespace.

        Returns:
            A UUID identifying this node instance. The same node name
            will always generate the same UUID across invocations.
        """
        # Try to get actual node_id if available, otherwise generate from name
        if hasattr(self, "_node_id") and isinstance(
            object.__getattribute__(self, "_node_id"), UUID
        ):
            return cast(UUID, object.__getattribute__(self, "_node_id"))
        # Generate deterministic UUID from node name using standard uuid5
        # Uses DNS namespace as a well-known namespace for name-based UUIDs
        return uuid.uuid5(uuid.NAMESPACE_DNS, self.get_node_name())

    def process(self, input_state: InputStateT) -> OutputStateT:
        """
        Process input state and return output state.

        Default implementation - override in subclasses for actual processing.

        Args:
            input_state: The typed input state to process.

        Returns:
            The typed output state after processing.

        Raises:
            NotImplementedError: If not overridden in subclass.
        """
        msg = "Subclasses must implement process method"
        raise NotImplementedError(msg)  # stub-ok: abstract method

    # --- Topic Validation ---

    def _validate_topic_alignment(
        self,
        topic: str,
        envelope: ProtocolEventEnvelope[object],
    ) -> None:
        """
        Validate that envelope's message category matches the topic.

        This method enforces message-topic alignment at runtime, ensuring that
        events are published to the correct topic type (e.g., events to .events
        topics, commands to .commands topics).

        Args:
            topic: Target Kafka topic
            envelope: Event envelope being published (must have message_category property)

        Raises:
            ModelOnexError: If message category doesn't match topic

        Example:
            >>> envelope = ModelEventEnvelope(payload=UserCreatedEvent(...))
            >>> self._validate_topic_alignment("dev.user.events.v1", envelope)  # OK
            >>> self._validate_topic_alignment("dev.user.commands.v1", envelope)  # Raises
        """
        # Only validate if envelope has message_category property
        if not hasattr(envelope, "message_category"):
            self._log_warn(
                f"Envelope type {type(envelope).__name__} does not have message_category property, skipping topic alignment validation",
                pattern="topic_alignment",
            )
            return

        message_category: EnumMessageCategory = envelope.message_category
        message_type_name = (
            type(envelope.payload).__name__
            if hasattr(envelope, "payload")
            else type(envelope).__name__
        )
        validate_message_topic_alignment(topic, message_category, message_type_name)

    # --- Event Completion Publishing ---

    async def publish_event(
        self,
        event_type: str,
        payload: ModelOnexEvent | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        """
        Publish an event via the event bus.

        This is a simple wrapper that publishes events directly to the event bus.

        Args:
            event_type: Type of event to publish
            payload: Event payload data (ModelOnexEvent or None for a new event)
            correlation_id: Optional correlation ID for tracking

        Raises:
            ModelOnexError: If event bus is not bound.
        """
        bus = self._require_event_bus()
        # Lock binding after first publish operation - any bind_*() after this warns
        self._lock_binding()

        try:
            # Build event using ModelOnexEvent or use provided payload
            event = payload or ModelOnexEvent.create_core_event(
                event_type=event_type,
                node_id=self.get_node_id(),
                correlation_id=correlation_id,
            )

            # Publish via event bus - fail fast if no publish method
            # TODO(OMN-TBD): [v1.0] Standardize event bus protocol to require publish_async().
            # Currently hasattr checks support legacy event bus implementations with
            # non-standard interfaces. Once all implementations conform to
            # ProtocolEventBus, these checks can be replaced with direct calls.
            # Cast to Any for duck-typed method calls.  [NEEDS TICKET]
            if hasattr(bus, "publish_async"):
                # Wrap in envelope for async publishing
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                    payload=event
                )
                # TODO(OMN-TBD): [v1.0] Add topic validation when topic-based publishing is implemented.
                # When the event bus supports explicit topic routing, validate alignment
                # between message category and topic name using _validate_topic_alignment().  [NEEDS TICKET]
                await cast(ProtocolEventBusDuckTyped, bus).publish_async(envelope)
            elif hasattr(bus, "publish"):
                cast(ProtocolEventBusDuckTyped, bus).publish(
                    event
                )  # Synchronous method - no await
            else:
                raise ModelOnexError(
                    message="Event bus does not support publishing (missing 'publish_async' and 'publish' methods)",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )

            self._log_info(f"Published event: {event_type}", event_type)

        except ModelOnexError:
            raise  # Re-raise structured errors without wrapping
        except (RuntimeError, TypeError, ValueError) as e:
            self._log_error(
                f"Failed to publish event: {e!r}",
                "publish_event",
                error=e,
            )

    def publish_completion_event(
        self,
        event_type: str,
        data: ModelCompletionData,
    ) -> None:
        """
        Publish completion event using synchronous event bus.

        Args:
            event_type: Event type string (e.g., "generation.health.complete")
            data: Completion data model

        Raises:
            ModelOnexError: If event bus is not bound.
        """
        bus = self._require_event_bus()
        # Lock binding after first publish operation - any bind_*() after this warns
        self._lock_binding()

        # Check if bus is async-only (has async methods but not sync methods)
        has_async = hasattr(bus, "apublish") or hasattr(bus, "apublish_async")
        has_sync = hasattr(bus, "publish") or hasattr(bus, "publish_async")

        if has_async and not has_sync:
            self._log_error(
                "registry.event_bus is async-only; call 'await apublish_completion_event(...)' instead",
                pattern="event_bus.async_only",
            )
            return

        try:
            event = self._build_event(event_type, data)
            # Use synchronous publish method only (this is a sync method) - fail fast if missing
            # TODO(OMN-TBD): [v1.0] Add topic validation when topic-based publishing is implemented.
            # Sync publish doesn't use envelope, so validation would need to wrap the event
            # in ModelEventEnvelope first before calling _validate_topic_alignment().  [NEEDS TICKET]
            # TODO(OMN-TBD): [v1.0] Standardize event bus protocol to require publish().
            # Currently hasattr check supports legacy event bus with non-standard interface.
            # Once all implementations conform to ProtocolEventBus, this check can be removed.  [NEEDS TICKET]
            if hasattr(bus, "publish"):
                cast(ProtocolEventBusDuckTyped, bus).publish(event)
            else:
                raise ModelOnexError(
                    message="Event bus has no synchronous 'publish' method",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )
            self._log_info(f"Published completion event: {event_type}", event_type)
        except ModelOnexError:
            raise  # Re-raise structured errors without wrapping
        except (RuntimeError, TypeError, ValueError) as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    async def apublish_completion_event(
        self,
        event_type: str,
        data: ModelCompletionData,
    ) -> None:
        """
        Publish completion event using asynchronous event bus.

        Supports both async and sync buses for maximum compatibility.

        Args:
            event_type: Event type string (e.g., "generation.health.complete")
            data: Completion data model

        Raises:
            ModelOnexError: If event bus is not bound.
        """
        bus = self._require_event_bus()
        # Lock binding after first publish operation - any bind_*() after this warns
        self._lock_binding()

        try:
            event = self._build_event(event_type, data)

            # Prefer async publishing if available - fail fast if no publish method
            # TODO(OMN-TBD): [v1.0] Standardize event bus protocol to require publish_async().
            # Currently hasattr checks support legacy event bus implementations with
            # non-standard interfaces. Once all implementations conform to
            # ProtocolEventBus, these checks can be replaced with direct calls.
            # Cast to Any for duck-typed method calls.  [NEEDS TICKET]
            if hasattr(bus, "publish_async"):
                # Wrap event in envelope for async publishing
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                    payload=event
                )
                # TODO(OMN-TBD): [v1.0] Add topic validation when topic-based publishing is implemented.
                # When the event bus supports explicit topic routing, validate alignment
                # between message category and topic name using _validate_topic_alignment().  [NEEDS TICKET]
                await cast(ProtocolEventBusDuckTyped, bus).publish_async(envelope)
            # Fallback to sync method
            elif hasattr(bus, "publish"):
                cast(ProtocolEventBusDuckTyped, bus).publish(
                    event
                )  # Synchronous method - no await
            else:
                raise ModelOnexError(
                    message="Event bus has no publish method (missing 'publish_async' and 'publish')",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )

            self._log_info(f"Published completion event: {event_type}", event_type)

        except ModelOnexError:
            raise  # Re-raise structured errors without wrapping
        except (RuntimeError, TypeError, ValueError) as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    def _build_event(
        self, event_type: str, data: ModelCompletionData
    ) -> ModelOnexEvent:
        """Build a ModelOnexEvent from completion data.

        Constructs a properly formatted ONEX event using the completion
        data's event kwargs, the node's ID, and optional correlation ID.

        Args:
            event_type: The event type string (e.g., "generation.health.complete").
            data: Completion data model containing message, success flag,
                tags, and optional correlation_id.

        Returns:
            A ModelOnexEvent instance ready for publishing via the event bus.

        Note:
            The correlation_id from data is extracted and passed separately
            to create_core_event() to ensure proper type handling.
        """
        # Extract kwargs and handle correlation_id explicitly
        event_kwargs = data.to_event_kwargs()
        correlation_id = event_kwargs.pop("correlation_id", None)

        return ModelOnexEvent.create_core_event(
            event_type=event_type,
            node_id=self.get_node_id(),
            correlation_id=correlation_id if isinstance(correlation_id, UUID) else None,
            **event_kwargs,
        )

    # --- Resource Cleanup ---

    def dispose_event_bus_resources(self) -> None:
        """Clean up all event bus publishing resources. Call on shutdown.

        This method is idempotent and safe to call multiple times. It will not
        raise exceptions for already-disposed resources.

        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads. It uses a lock-capture-release pattern:

            1. **Clear Bindings Phase (lock held)**: Atomically clear all
               bound attributes to prevent partial cleanup
            2. **Reset State Phase**: Reset runtime state to initial values

            The lock protects binding attribute modifications to ensure
            consistent state during cleanup.

        Error Handling:
            All cleanup errors are collected and logged. If any errors occur
            during cleanup, a ModelOnexError is raised after all cleanup steps
            complete, containing details of all failures. This ensures:

            1. All cleanup steps are attempted even if earlier steps fail
            2. Errors are not silently swallowed
            3. Callers are notified of cleanup failures via structured errors

        Raises:
            ModelOnexError: If any cleanup step fails. The error context contains
                a list of all errors encountered during cleanup.
        """
        cleanup_errors: list[str] = []

        try:
            # === Phase 1: Clear bindings atomically under lock ===
            with self._mixin_lock:
                for attr in (
                    "_bound_event_bus",
                    "_bound_registry",
                ):
                    try:
                        object.__delattr__(self, attr)
                    except AttributeError:
                        # AttributeError is EXPECTED during cleanup for two reasons:
                        # 1. Attribute was never bound (binding is optional)
                        # 2. Idempotent cleanup: dispose() called multiple times
                        #
                        # We log at DEBUG (not WARNING) because this is expected behavior.
                        emit_log_event(
                            LogLevel.DEBUG,
                            f"MIXIN_DISPOSE: Attribute {attr} not present during cleanup",
                            ModelLogData(node_name=self.get_node_name()),
                        )

            # === Phase 2: Reset runtime state ===
            try:
                self._event_bus_runtime_state.reset()
            except (AttributeError, RuntimeError) as e:
                cleanup_errors.append(f"Failed to reset runtime state: {e!r}")
                emit_log_event(
                    LogLevel.ERROR,
                    f"MIXIN_DISPOSE: Failed to reset runtime state: {e!r}",
                    ModelLogData(node_name=self.get_node_name()),
                )

        finally:
            # Log completion regardless of success/failure
            emit_log_event(
                LogLevel.DEBUG,
                "MIXIN_DISPOSE: Event bus resources disposed",
                ModelLogData(node_name=self.get_node_name()),
            )

        # Raise collected errors as structured ModelOnexError
        if cleanup_errors:
            raise ModelOnexError(
                message=f"Event bus cleanup completed with {len(cleanup_errors)} error(s)",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={
                    "node_name": self.get_node_name(),
                    "error_count": len(cleanup_errors),
                    "errors": cleanup_errors,
                },
            )

    # --- Logging Helpers ---

    def _log_info(self, msg: str, pattern: str) -> None:
        """Emit a structured INFO log with event pattern context.

        Args:
            msg: The log message to emit.
            pattern: Event pattern or operation identifier for context
                (e.g., "publish_completion", topic name).
        """
        emit_log_event(
            LogLevel.INFO,
            msg,
            context={"pattern": pattern, "node_name": self.get_node_name()},
        )

    def _log_warn(self, msg: str, pattern: str) -> None:
        """Emit a structured WARNING log with event pattern context.

        Args:
            msg: The warning message to emit.
            pattern: Event pattern or operation identifier for context.
        """
        emit_log_event(
            LogLevel.WARNING,
            msg,
            context={"pattern": pattern, "node_name": self.get_node_name()},
        )

    def _log_error(
        self,
        msg: str,
        pattern: str,
        error: BaseException | None = None,
    ) -> None:
        """Emit a structured ERROR log with event pattern and exception context.

        Args:
            msg: The error message to emit.
            pattern: Event pattern or operation identifier for context.
            error: Optional exception that caused the error. If provided,
                its repr() is included in the log context for debugging.
        """
        emit_log_event(
            LogLevel.ERROR,
            msg,
            context={
                "pattern": pattern,
                "node_name": self.get_node_name(),
                "error": None if error is None else repr(error),
            },
        )
