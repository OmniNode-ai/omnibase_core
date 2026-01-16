"""
Unified Event Bus Mixin for ONEX Nodes

Provides comprehensive event bus capabilities including:
- Event subscription and listening
- Event completion publishing
- Protocol-based polymorphism
- ONEX standards compliance
- Error handling and logging

This mixin uses composition with ModelEventBusRuntimeState and
ModelEventBusListenerHandle for state management, avoiding BaseModel
inheritance to prevent MRO conflicts in multi-inheritance scenarios.

Thread Safety:
    This mixin provides thread-safe stop() and dispose() operations.
    The internal _mixin_lock protects concurrent access to mutable state
    including listener handles and bindings. Multiple threads can safely
    call stop_event_listener() and dispose_event_bus_resources() concurrently.

    However, bind_*() methods are NOT thread-safe and should only be called
    during initialization before the mixin is shared across threads.

    Lock Hierarchy:
        - ``_class_init_lock`` (class-level): Protects lazy initialization of
          instance locks. Acquired only during first access to _mixin_lock.
        - ``_mixin_lock`` (instance-level): Protects mixin state mutations.
          Acquired during stop(), dispose(), and state-modifying operations.

        Never acquire _class_init_lock while holding _mixin_lock to avoid
        deadlocks.

    Thread Lifecycle:
        - Listener threads are daemon threads (auto-terminate on process exit)
        - dispose_event_bus_resources() explicitly joins listener threads with
          a 5-second timeout to ensure proper cleanup
        - Listener thread references are stored in ModelEventBusListenerHandle
          for lifecycle management

    Runtime Misuse Detection:
        The mixin tracks when it transitions to "in use" state via a
        _binding_locked flag. This flag is set to True when:
        - start_event_listener() is called (listener thread started)
        - publish_event() or publish_completion_event() operations occur

        If bind_*() methods are called after the flag is set, a ModelOnexError
        is raised (fail-fast behavior). This prevents thread-unsafe binding
        patterns from causing subtle race conditions in production.
"""

import threading
import uuid
from collections.abc import Callable
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

    def subscribe(self, handler: Callable[..., object], event_type: str) -> object:
        """Subscribe to events with a handler."""
        ...

    def unsubscribe(self, subscription: object) -> None:
        """Unsubscribe from events."""
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
from omnibase_core.protocols import ProtocolEventEnvelope, ProtocolFromEvent
from omnibase_core.protocols.event_bus import (
    ProtocolEventBus,
    ProtocolEventBusRegistry,
)

if TYPE_CHECKING:
    from omnibase_core.models.event_bus import (
        ModelEventBusListenerHandle,
        ModelEventBusRuntimeState,
    )


class MixinEventBus(Generic[InputStateT, OutputStateT]):
    """
    Unified mixin for all event bus operations in ONEX nodes.

    Provides:
    - Event listening and subscription capabilities
    - Completion event publishing with proper protocols
    - ONEX standards compliance (no dictionaries, proper models)
    - Protocol-based polymorphism for event bus access
    - Error handling and structured logging
    - Type-safe event processing via generic type parameters

    Design:
    - NO BaseModel inheritance (avoids MRO conflicts)
    - Explicit binding REQUIRED in __init__ before any operations
    - Composition with ModelEventBusRuntimeState and ModelEventBusListenerHandle
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
        - bind_contract_path(): Rejects empty or whitespace-only strings (raises ModelOnexError)
        - bind_event_bus(): Stores the event bus reference and sets is_bound=True
        - bind_registry(): Stores the registry and sets is_bound=True if registry.event_bus is available

        If no node_name is bound, get_node_name() falls back to class name.

    Reset vs Bind Behavior:
        - **bind_*() methods**: Set configuration values during initialization. These validate
          input and raise ModelOnexError for invalid values. Use in __init__ before the
          instance is shared across threads.
        - **_event_bus_runtime_state.reset()**: Clears the is_bound flag while preserving
          node_name and contract_path. Use for cleanup between operations (e.g., test teardown)
          or before rebinding with new configuration.
        - **dispose_event_bus_resources()**: Full cleanup that stops listeners, joins threads,
          clears all bindings, and resets runtime state. Use on shutdown.

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
        - publish_*(), stop_*(), dispose_*(): Safe for concurrent access after binding
        - Internal state protected by _mixin_lock (lazily initialized via class-level lock)

        See module docstring for detailed lock hierarchy and thread lifecycle documentation.

    Strict Binding Mode:
        By default (STRICT_BINDING_MODE=True), calling bind_*() methods after the mixin
        is "in use" (i.e., after start_event_listener() or publish operations) raises
        ModelOnexError with error_code=INVALID_STATE. This fail-fast behavior prevents
        subtle race conditions from reaching production.

        For gradual migration or compatibility with legacy code, disable strict mode:

            class MyLegacyNode(MixinEventBus[InputT, OutputT]):
                STRICT_BINDING_MODE: ClassVar[bool] = False

        When STRICT_BINDING_MODE is False, bind_*() calls after the mixin is in use will
        emit a WARNING log instead of raising an error.

        The default strict mode is recommended for:
        - Production systems where thread-unsafe patterns must be hard failures
        - CI/CD pipelines where errors are caught but warnings might be missed
        - New code where you want to enforce correct patterns from the start
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
    # the mixin is "in use" (after start_event_listener() or publish operations)
    # will raise ModelOnexError instead of just emitting a warning. Override in
    # subclasses to disable strict enforcement for legacy compatibility.
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
        stop and dispose operations. It is created lazily on first access
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

    @property
    def _event_bus_listener_handle(self) -> "ModelEventBusListenerHandle | None":
        """Accessor for listener handle - returns None if listener not started.

        The listener handle is created by start_event_listener() and stores
        the listener thread reference and subscriptions for cleanup.

        Returns:
            The ModelEventBusListenerHandle if start_event_listener() was called,
            None otherwise.
        """
        try:
            return cast(
                "ModelEventBusListenerHandle | None",
                object.__getattribute__(self, "_mixin_event_bus_listener"),
            )
        except AttributeError:
            return None

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
        because the mixin is being used by threads (listener started
        or publish operations have occurred).

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
        - start_event_listener() creates a listener thread
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

            Now bind_*() calls after start_event_listener() or publish will warn.
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
            is in use (after start_event_listener() or publish operations),
            a ModelOnexError is raised (STRICT_BINDING_MODE=True, default)
            or a WARNING is emitted (STRICT_BINDING_MODE=False).

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
            is in use (after start_event_listener() or publish operations),
            a ModelOnexError is raised (STRICT_BINDING_MODE=True, default)
            or a WARNING is emitted (STRICT_BINDING_MODE=False).

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

    def bind_contract_path(self, contract_path: str) -> None:
        """Bind the contract path used to derive event patterns.

        The contract path is used by get_event_patterns() to determine
        which event types this node should listen to and publish.

        Thread Safety:
            This method uses atomic check-and-bind under the mixin lock.
            It should only be called during __init__ before the mixin
            instance is shared across threads. If called after the mixin
            is in use (after start_event_listener() or publish operations),
            a ModelOnexError is raised (STRICT_BINDING_MODE=True, default)
            or a WARNING is emitted (STRICT_BINDING_MODE=False).

        Args:
            contract_path: Absolute or relative path to the ONEX contract
                YAML file that defines this node's event patterns. Must be
                a non-empty string. Use reset() on the runtime state to clear
                the binding if needed.

        Raises:
            ModelOnexError: If contract_path is empty or whitespace-only.
            ModelOnexError: If STRICT_BINDING_MODE is True and the mixin is
                already in use (binding is locked). Error code is INVALID_STATE.

        Note:
            The contract file is not loaded immediately; it is read when
            get_event_patterns() is called.

        Validation:
            This method validates that contract_path is non-empty and non-whitespace,
            consistent with ModelEventBusRuntimeState.bind() validation. To clear
            a previously bound contract path, use _event_bus_runtime_state.reset()
            followed by re-binding with the desired configuration.
        """
        # Validate contract_path BEFORE acquiring lock (fail-fast validation)
        if not contract_path or not contract_path.strip():
            raise ModelOnexError(
                message="contract_path must be a non-empty string for binding; "
                "use _event_bus_runtime_state.reset() to clear binding configuration",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                context={
                    "class_name": self.__class__.__name__,
                    "provided_value": repr(contract_path),
                },
            )

        # Ensure runtime state exists BEFORE acquiring lock
        # (state creation doesn't need lock protection)
        state = self._ensure_runtime_state()

        # Atomic check-and-bind under lock to prevent race conditions
        with self._mixin_lock:
            if self._is_binding_locked():
                message = (
                    "MIXIN_BIND: bind_contract_path() called after mixin is in use. "
                    "bind_*() methods should be called in __init__ before sharing across threads."
                )
                if self.STRICT_BINDING_MODE:
                    raise ModelOnexError(
                        message=message,
                        error_code=EnumCoreErrorCode.INVALID_STATE,
                        context={
                            "method_name": "bind_contract_path",
                            "node_name": self.get_node_name(),
                            "class_name": self.__class__.__name__,
                        },
                    )
                emit_log_event(
                    LogLevel.WARNING,
                    message,
                    ModelLogData(node_name=self.get_node_name()),
                )
            state.contract_path = contract_path

    def bind_node_name(self, node_name: str) -> None:
        """Bind the node name used for event publishing and logging.

        The node name is included in published events and log messages
        for identification and tracing purposes. If not bound, the
        class name is used as a fallback.

        Thread Safety:
            This method uses atomic check-and-bind under the mixin lock.
            It should only be called during __init__ before the mixin
            instance is shared across threads. If called after the mixin
            is in use (after start_event_listener() or publish operations),
            a ModelOnexError is raised (STRICT_BINDING_MODE=True, default)
            or a WARNING is emitted (STRICT_BINDING_MODE=False).

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
        correlation, logging context, and listener thread naming.

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

    # --- Event Listening and Subscription ---

    def get_event_patterns(self) -> list[str]:
        """Get event patterns this node should subscribe to and listen for.

        Default implementation generates patterns based on the node name.
        Override in subclasses for custom event subscription patterns.

        Returns:
            A list of event pattern strings that this node should subscribe to.
            Patterns follow the format "domain.node_name.action" (e.g.,
            "generation.mynode.start", "coordination.mynode.execute").

        Raises:
            ModelOnexError: If pattern generation fails due to configuration
                or contract parsing errors.

        Note:
            If contract_path is not bound or runtime state is not initialized,
            a warning is logged and an empty list is returned. Bind contract_path
            via bind_contract_path() before calling if you need contract-based patterns.

        Example:
            >>> node.bind_contract_path("/path/to/contract.yaml")
            >>> patterns = node.get_event_patterns()
            >>> # Returns ["generation.mynode.start", "generation.mynode.process", ...]
        """
        try:
            # Safe access to state - return empty list if state doesn't exist
            try:
                state = cast(
                    "ModelEventBusRuntimeState",
                    object.__getattribute__(self, "_mixin_event_bus_state"),
                )
                contract_path = state.contract_path
            except AttributeError:
                # State not initialized - treat as no contract_path
                contract_path = None

            if not contract_path:
                self._log_warn(
                    "No contract_path found, cannot determine event patterns",
                    "event_patterns",
                )
                return []

            # Extract event patterns from contract (simplified implementation)
            # Parse the YAML contract to extract event patterns
            node_name = self.get_node_name().lower()

            # Generate common patterns based on node name
            return [
                f"generation.{node_name}.start",
                f"generation.{node_name}.process",
                f"coordination.{node_name}.execute",
            ]

        except (AttributeError, KeyError, OSError, RuntimeError, ValueError) as e:
            self._log_error(
                f"Failed to get event patterns: {e!r}",
                "event_patterns",
                error=e,
            )
            raise ModelOnexError(
                f"Failed to get event patterns: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e

    def get_completion_event_type(self, input_event_type: str) -> str:
        """Get the completion event type for a given input event.

        Maps input event types to their corresponding completion event types
        using a predefined mapping table. This enables proper event-driven
        workflows where processing completion is signaled.

        Args:
            input_event_type: The input event type string to map
                (e.g., "generation.tool.start").

        Returns:
            The corresponding completion event type string
            (e.g., "generation.tool.complete").

        Raises:
            ModelOnexError: If event type mapping fails due to invalid format.

        Example:
            >>> event_type = node.get_completion_event_type("generation.tool.start")
            >>> # Returns "generation.tool.complete"
            >>> event_type = node.get_completion_event_type("custom.event")
            >>> # Returns "custom.complete" (default: replaces last part)
        """
        try:
            # input_event_type is already typed as str
            event_str = input_event_type

            # Extract domain and event suffix
            parts = event_str.split(".")
            if len(parts) < 3:
                return f"{event_str}.complete"

            domain = parts[0]  # e.g., "generation"
            event_suffix = ".".join(parts[1:])  # e.g., "tool.start"

            # Map input events to completion events
            completion_mappings = {
                "health.check": "health.complete",
                "contract.validate": "contract.complete",
                "tool.start": "tool.complete",
                "tool.process": "tool.complete",
                "ast.generate": "ast.complete",
                "render.files": "render.complete",
                "validate.files": "validate.complete",
            }

            # Find matching pattern
            for pattern, completion in completion_mappings.items():
                if event_suffix.endswith(pattern.split(".")[-1]):
                    return f"{domain}.{completion}"

            # Default: replace last part with "complete"
            parts[-1] = "complete"
            return ".".join(parts)

        except (IndexError, TypeError, ValueError) as e:
            self._log_error(
                f"Failed to determine completion event type: {e!r}",
                "completion_event_type",
                error=e,
            )
            raise ModelOnexError(
                f"Failed to determine completion event type: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e

    def start_event_listener(self) -> "ModelEventBusListenerHandle":
        """Start the event listener thread for processing incoming events.

        Creates a background daemon thread that subscribes to event patterns
        returned by get_event_patterns() and dispatches incoming events to
        the process() method. This method is idempotent - calling it when
        a listener is already running returns the existing handle.

        Returns:
            A ModelEventBusListenerHandle for managing the listener lifecycle.
            Use the handle's stop() method or stop_event_listener() to terminate.

        Raises:
            ModelOnexError: If no event bus is bound. Call bind_event_bus()
                or bind_registry() before starting the listener.

        Note:
            The listener thread is a daemon thread, meaning it will be
            automatically terminated when the main program exits.

        Example:
            >>> node.bind_event_bus(event_bus)
            >>> handle = node.start_event_listener()
            >>> # ... process events ...
            >>> node.stop_event_listener(handle)
        """
        from omnibase_core.models.event_bus import ModelEventBusListenerHandle

        # Return existing handle if already running
        existing = self._event_bus_listener_handle
        if existing is not None and existing.is_active():
            self._log_warn("Event listener already running", "event_listener")
            return existing

        if not self._has_event_bus():
            raise ModelOnexError(
                message=f"Cannot start event listener on {self.__class__.__name__}: "
                "no event bus available. Call bind_event_bus() or bind_registry() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={"class_name": self.__class__.__name__},
            )

        # Lock binding before starting listener thread - any bind_*() after this warns
        self._lock_binding()

        # Create new handle
        handle = ModelEventBusListenerHandle(
            stop_event=threading.Event(),
            is_running=True,
        )

        # Create and start thread
        handle.listener_thread = threading.Thread(
            target=self._event_listener_loop,
            args=(handle,),
            daemon=True,
            name=f"EventListener-{self.get_node_name()}",
        )
        handle.listener_thread.start()

        # Store handle
        object.__setattr__(self, "_mixin_event_bus_listener", handle)

        self._log_info("Event listener started", "event_listener")
        return handle

    def stop_event_listener(
        self, handle: "ModelEventBusListenerHandle | None" = None
    ) -> bool:
        """Stop the event listener and unsubscribe from all events.

        Gracefully terminates the event listener thread and removes all
        event subscriptions from the event bus. This method is safe to
        call multiple times - it will not raise errors if the listener
        is already stopped or was never started.

        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads. It uses a three-phase lock pattern:

            1. **Phase 1 (lock held)**: Capture handle and bus references.
               Also checks is_running inside the lock for consistency - if
               the listener is already stopped, returns immediately to avoid
               unnecessary work and prevent race conditions.
            2. **Phase 2 (lock released)**: Perform unsubscription and stop
               (potentially blocking operations)
            3. **Cleanup**: Handle errors after stop completes

            The lock is released before blocking operations to allow other
            threads to proceed. The captured references remain valid because
            Python's reference counting keeps objects alive.

        Args:
            handle: Optional listener handle to stop. If None, stops the
                current listener associated with this mixin instance.

        Returns:
            True if the listener was stopped cleanly within the timeout
            period or if there was no active listener. False if the
            listener thread did not terminate within the timeout.

        Raises:
            ModelOnexError: If the event bus does not support unsubscribe().
                Note: Even when this is raised, the listener thread is still
                stopped to prevent resource leaks.

        Note:
            Unsubscription errors are logged but do not prevent stopping
            the listener thread. Check logs for any failed unsubscriptions.
        """
        # === Phase 1: Capture references under lock ===
        with self._mixin_lock:
            target = handle or self._event_bus_listener_handle
            if target is None:
                return True  # Nothing to stop

            # Check is_running inside lock for consistency
            # This prevents unnecessary work if another thread already stopped the listener
            if not target.is_running:
                return True  # Already stopped

            # Capture bus reference under lock for thread safety
            bus = self._get_event_bus()
            # Copy subscriptions list to avoid iteration issues if modified
            subscriptions_copy = (
                list(target.subscriptions) if target.subscriptions else []
            )
        # Lock released here - other threads can now access state

        # === Phase 2: Unsubscribe and stop (lock NOT held) ===
        # Perform potentially blocking operations outside the lock
        unsubscribe_error: ModelOnexError | None = None

        # Unsubscribe from all events - fail fast if bus doesn't support unsubscribe
        # but still call target.stop() to prevent resource leaks
        # TODO(OMN-TBD): [v1.0] Standardize event bus protocol to require unsubscribe().
        # Currently hasattr check supports legacy event bus implementations.  [NEEDS TICKET]
        if bus and subscriptions_copy:
            if not hasattr(bus, "unsubscribe"):
                # Capture error but continue to stop the listener thread
                unsubscribe_error = ModelOnexError(
                    message="Event bus does not support 'unsubscribe' method",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__},
                )
            else:
                for subscription in subscriptions_copy:
                    try:
                        # Cast to Any for legacy event bus interface
                        cast(ProtocolEventBusDuckTyped, bus).unsubscribe(subscription)
                    except Exception as e:
                        self._log_error(
                            f"Failed to unsubscribe: {e!r}",
                            "event_listener",
                            error=e,
                        )

        # Always stop the listener thread, even if unsubscription failed
        # target.stop() is already thread-safe (has its own internal lock)
        result = target.stop()
        self._log_info("Event listener stopped", "event_listener")

        # Re-raise unsubscribe error after ensuring listener is stopped
        if unsubscribe_error is not None:
            raise unsubscribe_error

        return result

    def dispose_event_bus_resources(self) -> None:
        """Clean up all event bus resources. Call on shutdown.

        This method is idempotent and safe to call multiple times. It will not
        raise exceptions for already-disposed resources.

        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads. It uses a lock-capture-release pattern:

            1. **Capture Phase (lock held)**: Capture references to handle
               and state, set disposed flag to prevent re-entry
            2. **Cleanup Phase (lock released)**: Stop listener thread and
               perform potentially blocking cleanup operations
            3. **Thread Join Phase**: Explicitly join listener thread with the
               handle's configured timeout to ensure thread termination before proceeding
            4. **Binding Cleanup Phase (lock held)**: Atomically clear all
               bound attributes to prevent partial cleanup

            The lock is released during blocking operations to allow other
            threads to proceed. All cleanup phases are wrapped in try/finally
            to ensure resources are released even if exceptions occur.

        Listener Thread Cleanup:
            Listener threads are explicitly joined to ensure proper resource
            cleanup. The join uses the handle's configured timeout (default 5.0
            seconds via ModelEventBusListenerHandle.DEFAULT_STOP_TIMEOUT) to
            prevent indefinite blocking. If the thread does not terminate within
            this timeout, a warning is logged and included in the cleanup errors,
            but cleanup continues to release other resources.

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
        from omnibase_core.models.event_bus import ModelEventBusListenerHandle

        cleanup_errors: list[str] = []
        handle: ModelEventBusListenerHandle | None = None

        try:
            # === Phase 1: Capture handle reference under lock ===
            with self._mixin_lock:
                handle = self._event_bus_listener_handle
            # Lock released - other threads can access state

            # === Phase 2: Stop listener (lock NOT held - may block) ===
            # Use stop_event_listener() to properly unsubscribe from the event bus
            # before stopping. This prevents memory leaks where the event bus retains
            # references to dead subscriptions. stop_event_listener() handles its own
            # thread safety with internal locks.
            if handle is not None:
                try:
                    # stop_event_listener() properly:
                    # 1. Gets event bus reference
                    # 2. Unsubscribes from all events
                    # 3. Calls handle.stop()
                    # This prevents memory leaks in the event bus
                    stopped = self.stop_event_listener(handle)
                    if not stopped:
                        cleanup_errors.append(
                            "Event listener did not stop within timeout"
                        )
                except (ModelOnexError, RuntimeError, ValueError) as e:
                    # stop_event_listener() may raise ModelOnexError if event bus
                    # doesn't support unsubscribe, but it still stops the listener
                    cleanup_errors.append(f"Failed to stop event listener: {e!r}")
                    emit_log_event(
                        LogLevel.ERROR,
                        f"MIXIN_DISPOSE: Failed to stop event listener: {e!r}",
                        ModelLogData(node_name=self.get_node_name()),
                    )

                # Explicitly join listener thread for proper cleanup
                # This ensures the thread has fully terminated before we continue
                if handle.listener_thread is not None:
                    try:
                        # Use the handle's configured timeout for consistency
                        # This respects instance/class-level timeout configuration
                        join_timeout = handle.get_stop_timeout()
                        handle.listener_thread.join(timeout=join_timeout)
                        if handle.listener_thread.is_alive():
                            cleanup_errors.append(
                                "Listener thread did not terminate within join timeout"
                            )
                            emit_log_event(
                                LogLevel.WARNING,
                                "MIXIN_DISPOSE: Listener thread did not terminate within timeout",
                                ModelLogData(node_name=self.get_node_name()),
                            )
                    except (OSError, RuntimeError) as e:
                        cleanup_errors.append(f"Failed to join listener thread: {e!r}")
                        emit_log_event(
                            LogLevel.ERROR,
                            f"MIXIN_DISPOSE: Failed to join listener thread: {e!r}",
                            ModelLogData(node_name=self.get_node_name()),
                        )

            # === Phase 3: Clear bindings atomically under lock ===
            with self._mixin_lock:
                for attr in (
                    "_bound_event_bus",
                    "_bound_registry",
                    "_mixin_event_bus_listener",
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

            # === Phase 4: Reset runtime state ===
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

    def _event_listener_loop(self, handle: "ModelEventBusListenerHandle") -> None:
        """Run the main event listener loop in a background thread.

        Subscribes to all event patterns from get_event_patterns() and waits
        for incoming events. The loop runs until the handle's stop_event is
        set or an unrecoverable error occurs.

        Args:
            handle: The listener handle containing the stop event and
                subscription list. Subscriptions are stored in the handle
                for cleanup during stop_event_listener().

        Note:
            This method is intended to be run in a daemon thread started
            by start_event_listener(). It should not be called directly.
            Subscription failures are logged but do not stop the loop.
        """
        try:
            patterns = self.get_event_patterns()
            if not patterns:
                self._log_warn("No event patterns to listen to", "event_listener")
                return

            bus = self._get_event_bus()
            if not bus:
                raise ModelOnexError(
                    message="No event bus available for subscription",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"node_name": self.get_node_name()},
                )

            # TODO(OMN-TBD): [v1.0] Standardize event bus protocol to require subscribe().
            # Currently hasattr check supports legacy event bus implementations.  [NEEDS TICKET]
            if not hasattr(bus, "subscribe"):
                raise ModelOnexError(
                    message="Event bus does not support 'subscribe' method",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={
                        "bus_type": type(bus).__name__,
                        "node_name": self.get_node_name(),
                    },
                )

            # Subscribe to all patterns
            # Note: Cast to Any for legacy event bus interface
            for pattern in patterns:
                try:
                    event_handler = self._create_event_handler(pattern)
                    subscription = cast(ProtocolEventBusDuckTyped, bus).subscribe(
                        event_handler, event_type=pattern
                    )
                    handle.subscriptions.append(subscription)
                    self._log_info(f"Subscribed to pattern: {pattern}", pattern)
                except (RuntimeError, TypeError, ValueError) as e:
                    self._log_error(
                        f"Failed to subscribe to {pattern}: {e!r}",
                        "subscribe",
                        error=e,
                    )

            # Keep thread alive
            while handle.stop_event is not None and not handle.stop_event.wait(1.0):
                pass

        except (RuntimeError, ValueError) as e:
            self._log_error(
                f"Event listener loop failed: {e!r}",
                "event_listener",
                error=e,
            )

    def _create_event_handler(
        self, pattern: str
    ) -> Callable[[ProtocolEventEnvelope[ModelOnexEvent]], None]:
        """Create an event handler closure for a specific event pattern.

        Generates a handler function that extracts events from envelopes,
        converts them to typed input state, processes them via process(),
        and publishes completion events.

        Args:
            pattern: The event pattern string this handler will process
                (e.g., "generation.mynode.start"). Used for logging and
                error context.

        Returns:
            A callable handler function that accepts ProtocolEventEnvelope
            and processes the contained event. The handler manages its own
            error handling and publishes error completion events on failure.

        Note:
            The returned handler captures the pattern in its closure for
            logging and error reporting. Each pattern should have its own
            handler instance.
        """

        def handler(envelope: ProtocolEventEnvelope[ModelOnexEvent]) -> None:
            """Handle incoming event envelope."""
            # Extract event from envelope - fail fast if missing
            if not hasattr(envelope, "payload"):
                raise ModelOnexError(
                    message=f"Envelope missing required 'payload' attribute for pattern {pattern}",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                    context={
                        "pattern": pattern,
                        "envelope_type": type(envelope).__name__,
                    },
                )

            event: ModelOnexEvent = envelope.payload

            # Validate event has required attributes - fail fast if missing
            if not hasattr(event, "event_type"):
                raise ModelOnexError(
                    message=f"Event missing required 'event_type' attribute for pattern {pattern}",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                    context={"pattern": pattern, "event_type": type(event).__name__},
                )

            try:
                self._log_info(
                    f"Processing event: {event.event_type}",
                    str(event.event_type),
                )

                # Convert event to input state
                input_state = self._event_to_input_state(event)

                # Process through the node
                self.process(input_state)

                # Publish completion event
                completion_event_type = self.get_completion_event_type(
                    str(event.event_type)
                )
                completion_data = ModelCompletionData(
                    message=f"Processing completed for {event.event_type}",
                    success=True,
                    tags=["processed", "completed"],
                )

                self.publish_completion_event(completion_event_type, completion_data)

                self._log_info(
                    f"Event processing completed: {event.event_type}",
                    str(event.event_type),
                )

            except Exception as e:  # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
                self._log_error(f"Event processing failed: {e!r}", pattern, error=e)

                # Publish error completion event
                try:
                    completion_event_type = self.get_completion_event_type(
                        str(event.event_type),
                    )
                    error_data = ModelCompletionData(
                        message=f"Processing failed: {e!s}",
                        success=False,
                        tags=["error", "failed"],
                    )
                    self.publish_completion_event(completion_event_type, error_data)
                except (ModelOnexError, RuntimeError, ValueError) as publish_error:
                    self._log_error(
                        f"Failed to publish error event: {publish_error!r}",
                        "publish_error",
                        error=publish_error,
                    )

        return handler

    def _event_to_input_state(self, event: ModelOnexEvent) -> InputStateT:
        """Convert ModelOnexEvent to typed input state for processing.

        Args:
            event: The incoming event to convert.

        Returns:
            The typed input state extracted from the event.

        Raises:
            ModelOnexError: If event is not a ModelOnexEvent or if input state
                class cannot be determined.
        """
        # Type guard: validate event parameter is actually ModelOnexEvent
        if not isinstance(event, ModelOnexEvent):
            raise ModelOnexError(
                message=f"Expected ModelOnexEvent, got {type(event).__name__}",
                error_code=EnumCoreErrorCode.TYPE_MISMATCH,
                context={
                    "expected_type": "ModelOnexEvent",
                    "actual_type": type(event).__name__,
                    "node_name": self.get_node_name(),
                },
            )

        try:
            input_state_class = self._get_input_state_class()
            if not input_state_class:
                msg = "Cannot determine input state class for event conversion"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )

            # Extract data from event - convert to dict if ModelEventData
            event_data_raw = event.data
            if event_data_raw is None:
                event_data: dict[str, object] = {}
            elif hasattr(event_data_raw, "model_dump"):
                event_data = event_data_raw.model_dump()
            else:
                event_data = {}

            # Try to create input state from event data using from_event if available
            # Use Protocol-based type narrowing for proper type safety
            if isinstance(input_state_class, type) and issubclass(
                input_state_class, ProtocolFromEvent
            ):
                # Protocol check passed - from_event method exists and is callable
                result: InputStateT = cast(
                    InputStateT, input_state_class.from_event(event)
                )
                return result

            # Fallback: check for from_event via getattr for classes that don't
            # match the Protocol (e.g., due to signature differences)
            # TODO(OMN-TBD): [v1.0] Remove this fallback after migration to ProtocolFromEvent.
            # This supports legacy input state classes that have from_event but don't
            # conform to the ProtocolFromEvent signature. Once all consumers have
            # migrated to the protocol-based pattern, this can be removed.  [NEEDS TICKET]
            from_event_method = getattr(input_state_class, "from_event", None)
            if from_event_method is not None and callable(from_event_method):
                result = cast(InputStateT, from_event_method(event))
                return result

            # Verify class is callable before invoking
            if not callable(input_state_class):
                raise ModelOnexError(
                    message=f"Input state class {input_state_class} is not callable",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                    context={"input_state_class": str(input_state_class)},
                )
            # Create from event data directly
            return cast(InputStateT, input_state_class(**event_data))

        except (KeyError, TypeError, ValueError) as e:
            self._log_error(
                f"Failed to convert event to input state: {e!r}",
                "event_conversion",
                error=e,
            )
            raise

    def _get_input_state_class(self) -> type | None:
        """Extract the input state class from generic type parameters.

        Uses Python's type introspection to find the InputStateT type
        argument from the class's generic bases. This enables type-safe
        event-to-state conversion in _event_to_input_state().

        Returns:
            The input state class (first generic type argument) or None
            if the class was not parameterized with concrete types.

        Raises:
            ModelOnexError: If type introspection fails due to unexpected
                AttributeError, TypeError, or IndexError.

        Example:
            >>> class MyNode(MixinEventBus[MyInputState, MyOutputState]): ...
            >>> node = MyNode()
            >>> node._get_input_state_class()  # Returns MyInputState
        """
        try:
            # Get the generic type arguments
            orig_bases = getattr(self.__class__, "__orig_bases__", ())
            for base in orig_bases:
                if hasattr(base, "__args__") and len(base.__args__) >= 1:
                    cls: type | None = base.__args__[0]
                    return cls
            return None
        except (AttributeError, IndexError, TypeError) as e:
            # Fail fast on unexpected errors during type introspection
            raise ModelOnexError(
                message=f"Failed to extract input state class from generic type parameters: {e!s}",
                error_code=EnumCoreErrorCode.TYPE_INTROSPECTION_ERROR,
                context={
                    "node_name": self.get_node_name(),
                    "class_name": self.__class__.__name__,
                    "error_type": type(e).__name__,
                },
            ) from e

    # --- Logging Helpers ---

    def _log_info(self, msg: str, pattern: str) -> None:
        """Emit a structured INFO log with event pattern context.

        Args:
            msg: The log message to emit.
            pattern: Event pattern or operation identifier for context
                (e.g., "event_listener", "publish_completion", topic name).
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
