"""
Message Dispatch Engine.

Runtime dispatch engine for routing messages based on topic category and
message type. Routes incoming messages to registered handlers and collects
handler outputs for publishing.

Design Principles:
    - **Pure Routing**: Routes messages to handlers, no workflow inference
    - **Deterministic**: Same input always produces same handler selection
    - **Fan-out Support**: Multiple handlers can process the same message type
    - **Freeze-After-Init**: Thread-safe after registration phase completes
    - **Observable**: Structured logging and comprehensive metrics

Architecture:
    The dispatch engine provides:
    - Route registration for topic pattern matching
    - Handler registration by category and message type
    - Message dispatch with category validation
    - Metrics collection for observability
    - Structured logging for debugging and monitoring

    It does NOT:
    - Infer workflow semantics from message content
    - Manage handler lifecycle (handlers are external)
    - Perform message transformation or enrichment
    - Make decisions about message ordering or priority

Data Flow:
    ```
    +------------------------------------------------------------------+
    |                   Message Dispatch Engine                         |
    +------------------------------------------------------------------+
    |                                                                  |
    |   1. Parse Topic       2. Validate          3. Match Handlers    |
    |        |                   |                       |             |
    |        |  topic string     |  category match       |             |
    |        |-------------------|----------------------|             |
    |        |                   |                       |             |
    |        | EnumMessageCategory                       | handlers[]  |
    |        |<------------------|                       |------------>|
    |        |                   |                       |             |
    |   4. Execute Handlers  5. Collect Outputs   6. Return Result    |
    |        |                   |                       |             |
    |        | handler outputs   |  aggregate           |             |
    |        |-------------------|----------------------|             |
    |        |                   |                       |             |
    |        |                   |  ModelDispatchResult  |             |
    |        |<------------------|<---------------------|             |
    |                                                                  |
    +------------------------------------------------------------------+
    ```

Thread Safety:
    MessageDispatchEngine follows the "freeze after init" pattern:

    1. **Registration Phase** (single-threaded): Register routes and handlers
    2. **Freeze**: Call freeze() to prevent further modifications
    3. **Dispatch Phase** (multi-threaded safe): Route messages to handlers

    After freeze(), the engine becomes read-only and can be safely shared
    across threads for concurrent dispatch operations.

Related:
    - OMN-934: Message dispatch engine implementation
    - EnvelopeRouter: Transport-agnostic orchestrator (reference for freeze pattern)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["MessageDispatchEngine"]

import asyncio
import inspect
import logging
import threading
import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.compute.model_compute_context import ModelComputeContext
from omnibase_core.models.dispatch.model_dispatch_metrics import ModelDispatchMetrics
from omnibase_core.models.dispatch.model_dispatch_result import ModelDispatchResult
from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.models.dispatch.model_handler_metrics import ModelHandlerMetrics
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.effect.model_effect_context import ModelEffectContext
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.orchestrator.model_orchestrator_context import (
    ModelOrchestratorContext,
)
from omnibase_core.models.reducer.model_reducer_context import ModelReducerContext
from omnibase_core.protocols.event_bus.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocols.handler.protocol_handler_context import (
    ProtocolHandlerContext,
)
from omnibase_core.types.typed_dict_legacy_dispatch_metrics import (
    TypedDictLegacyDispatchMetrics,
)
from omnibase_core.types.typed_dict_log_context import TypedDictLogContext

# Module-level logger for fallback when no custom logger is provided
_module_logger = logging.getLogger(__name__)

# Type alias for valid metric keys (must match TypedDictLegacyDispatchMetrics keys)
MetricKey = Literal[
    "dispatch_count",
    "dispatch_success_count",
    "dispatch_error_count",
    "total_latency_ms",
    "handler_execution_count",
    "handler_error_count",
    "routes_matched_count",
    "no_handler_count",
    "category_mismatch_count",
]

# Type alias for handler return types (without Awaitable wrapper)
HandlerReturnType = ModelHandlerOutput[object] | str | list[object]

# Type alias for sync handler functions (used for run_in_executor narrowing)
SyncHandlerFunc = Callable[
    [ModelEventEnvelope[object], ProtocolHandlerContext],
    HandlerReturnType,
]

# Type alias for handler functions
# Handlers take an envelope and context, can be sync or async
# Return type accommodates:
# - ModelHandlerOutput[object] (new pattern)
# - str (legacy topic strings)
# - list[object] (legacy list of topic strings)
HandlerFunc = Callable[
    [ModelEventEnvelope[object], ProtocolHandlerContext],
    HandlerReturnType | Awaitable[HandlerReturnType],
]


class MessageDispatchEngine:
    """
    Runtime dispatch engine for message routing.

    Routes messages based on topic category and message type to registered
    handlers. Supports fan-out (multiple handlers per message type) and
    collects handler outputs for publishing.

    Key Characteristics:
        - **Pure Routing**: No workflow inference or semantic understanding
        - **Deterministic**: Same input always produces same handler selection
        - **Fan-out**: Multiple handlers can process the same message type
        - **Observable**: Structured logging and comprehensive metrics

    Registration Semantics:
        - **Routes**: Keyed by route_id, duplicates raise error
        - **Handlers**: Keyed by handler_id, duplicates raise error
        - Both must complete before freeze() is called

    Thread Safety:
        Follows the freeze-after-init pattern. All registrations must complete
        before calling freeze(). After freeze(), dispatch operations are
        thread-safe for concurrent access.

    Logging Levels:
        - **INFO**: Dispatch start/complete with topic, category, handler count
        - **DEBUG**: Handler execution details, routing decisions
        - **WARNING**: No handlers found, category mismatches
        - **ERROR**: Handler exceptions, validation failures

    Example:
        >>> from omnibase_core.runtime import MessageDispatchEngine
        >>> from omnibase_core.models.dispatch import ModelDispatchRoute
        >>> from omnibase_core.enums import EnumMessageCategory
        >>>
        >>> # Create engine with optional custom logger
        >>> engine = MessageDispatchEngine(logger=my_logger)
        >>> engine.register_handler(
        ...     handler_id="user-handler",
        ...     handler=process_user_event,
        ...     category=EnumMessageCategory.EVENT,
        ...     message_types={"UserCreated", "UserUpdated"},
        ... )
        >>> engine.register_route(ModelDispatchRoute(
        ...     route_id="user-route",
        ...     topic_pattern="*.user.events.*",
        ...     message_category=EnumMessageCategory.EVENT,
        ...     handler_id="user-handler",
        ... ))
        >>> engine.freeze()
        >>>
        >>> # Dispatch (thread-safe after freeze)
        >>> result = await engine.dispatch("dev.user.events.v1", envelope)

    Attributes:
        _routes: Registry of routes by route_id
        _handlers: Registry of handlers by handler_id
        _handlers_by_category: Index of handlers by category for fast lookup
        _frozen: If True, registration methods raise ModelOnexError
        _registration_lock: Lock protecting registration methods
        _structured_metrics: Pydantic-based metrics model for observability
        _logger: Optional custom logger for structured logging

    See Also:
        - :class:`~omnibase_core.models.dispatch.ModelDispatchRoute`: Route model
        - :class:`~omnibase_core.models.dispatch.ModelDispatchResult`: Result model
        - :class:`~omnibase_core.models.dispatch.ModelDispatchMetrics`: Metrics model
        - :class:`~omnibase_core.runtime.EnvelopeRouter`: Reference implementation

    .. versionadded:: 0.4.0
    """

    class _HandlerEntry:
        """Internal storage for handler registration metadata."""

        __slots__ = ("category", "handler", "handler_id", "message_types", "node_kind")

        def __init__(
            self,
            handler_id: str,
            handler: HandlerFunc,
            category: EnumMessageCategory,
            message_types: set[str] | None,
            node_kind: EnumNodeKind,
        ) -> None:
            self.handler_id = handler_id
            self.handler = handler
            self.category = category
            self.message_types = message_types  # None means "all types"
            self.node_kind = node_kind

    def __init__(
        self,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize MessageDispatchEngine with empty registries.

        Creates empty route and handler registries and initializes metrics.
        Call freeze() after registration to enable thread-safe dispatch.

        Args:
            logger: Optional custom logger for structured logging.
                If not provided, uses module-level logger.
        """
        # Optional custom logger
        self._logger: logging.Logger = logger if logger is not None else _module_logger

        # Route storage: route_id -> ModelDispatchRoute
        self._routes: dict[str, ModelDispatchRoute] = {}

        # Handler storage: handler_id -> _HandlerEntry
        self._handlers: dict[str, MessageDispatchEngine._HandlerEntry] = {}

        # Index for fast handler lookup by category
        # category -> list of handler_ids
        self._handlers_by_category: dict[EnumMessageCategory, list[str]] = {
            EnumMessageCategory.EVENT: [],
            EnumMessageCategory.COMMAND: [],
            EnumMessageCategory.INTENT: [],
        }

        # Freeze state
        self._frozen: bool = False
        self._registration_lock: threading.Lock = threading.Lock()

        # Metrics lock for thread-safe metrics updates
        # Python's += is NOT atomic - it's a read-modify-write operation
        self._metrics_lock: threading.Lock = threading.Lock()

        # Structured metrics (Pydantic model)
        self._structured_metrics: ModelDispatchMetrics = ModelDispatchMetrics()

        # Dictionary metrics (alternative format for introspection)
        self._metrics: TypedDictLegacyDispatchMetrics = {
            "dispatch_count": 0,
            "dispatch_success_count": 0,
            "dispatch_error_count": 0,
            "total_latency_ms": 0.0,
            "handler_execution_count": 0,
            "handler_error_count": 0,
            "routes_matched_count": 0,
            "no_handler_count": 0,
            "category_mismatch_count": 0,
        }

    def register_route(self, route: ModelDispatchRoute) -> None:
        """
        Register a routing rule.

        Routes define how messages are matched to handlers based on topic
        pattern, message category, and optionally message type.

        Args:
            route: The routing rule to register. Must have unique route_id.

        Raises:
            ModelOnexError: If engine is frozen (INVALID_STATE)
            ModelOnexError: If route is None (INVALID_PARAMETER)
            ModelOnexError: If route with same route_id exists (DUPLICATE_REGISTRATION)
            ModelOnexError: If route.handler_id references non-existent handler
                (ITEM_NOT_REGISTERED) - only checked after freeze

        Example:
            >>> engine.register_route(ModelDispatchRoute(
            ...     route_id="order-events",
            ...     topic_pattern="*.order.events.*",
            ...     message_category=EnumMessageCategory.EVENT,
            ...     handler_id="order-handler",
            ... ))

        Note:
            Route-to-handler consistency is NOT validated during registration
            to allow flexible registration order. Validation occurs at freeze()
            time or during dispatch.
        """
        if route is None:
            raise ModelOnexError(
                message=(
                    "Cannot register None route. "
                    "Provide a valid ModelDispatchRoute instance with topic_pattern, handler_id, and message_category."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        with self._registration_lock:
            if self._frozen:
                raise ModelOnexError(
                    message=(
                        f"Cannot register route '{route.route_id}': MessageDispatchEngine is frozen. "
                        "Registration is not allowed after freeze() has been called. "
                        "Register all routes before calling freeze()."
                    ),
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )

            if route.route_id in self._routes:
                existing_route = self._routes[route.route_id]
                raise ModelOnexError(
                    message=(
                        f"Route with ID '{route.route_id}' is already registered. "
                        f"Existing route: pattern='{existing_route.topic_pattern}', handler='{existing_route.handler_id}'. "
                        f"Use a unique route_id or unregister the existing route first."
                    ),
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                )

            self._routes[route.route_id] = route
            self._logger.debug(
                "Registered route '%s' for pattern '%s' (category=%s, handler=%s)",
                route.route_id,
                route.topic_pattern,
                route.message_category,
                route.handler_id,
            )

    def register_handler(
        self,
        handler_id: str,
        handler: HandlerFunc,
        category: EnumMessageCategory,
        node_kind: EnumNodeKind,
        message_types: set[str] | None = None,
    ) -> None:
        """
        Register a message handler.

        Handlers process messages that match their category and (optionally)
        message type. Multiple handlers can register for the same category
        and message type (fan-out pattern).

        Args:
            handler_id: Unique identifier for this handler
            handler: Callable that processes messages. Can be sync or async.
                Signature: (envelope: ModelEventEnvelope[object], context: ProtocolHandlerContext) -> ModelHandlerOutput[object]
            category: Message category this handler processes
            node_kind: The architectural node kind for this handler. Determines
                which context type the handler receives:
                - EFFECT: ModelEffectContext (with `now`, `retry_attempt`)
                - COMPUTE: ModelComputeContext (no `now` - pure function)
                - REDUCER: ModelReducerContext (no `now` - pure function)
                - ORCHESTRATOR: ModelOrchestratorContext (with `now`)
                RUNTIME_HOST is not allowed as it's for infrastructure, not handlers.
            message_types: Optional set of specific message types to handle.
                When None, handles all message types in the category.

        Raises:
            ModelOnexError: If engine is frozen (INVALID_STATE)
            ModelOnexError: If handler_id is empty (INVALID_PARAMETER)
            ModelOnexError: If handler is not callable (INVALID_PARAMETER)
            ModelOnexError: If node_kind is RUNTIME_HOST (INVALID_PARAMETER)
            ModelOnexError: If handler with same ID exists (DUPLICATE_REGISTRATION)

        Example:
            >>> async def process_user_event(envelope, context):
            ...     # Access correlation tracking
            ...     logger.info(f"Processing {context.correlation_id}")
            ...     user_data = envelope.payload
            ...     return {"processed": True}
            >>>
            >>> engine.register_handler(
            ...     handler_id="user-event-handler",
            ...     handler=process_user_event,
            ...     category=EnumMessageCategory.EVENT,
            ...     node_kind=EnumNodeKind.REDUCER,
            ...     message_types={"UserCreated", "UserUpdated"},
            ... )

        Note:
            Handlers are NOT automatically linked to routes. You must register
            routes separately that reference the handler_id.
        """
        # Validate inputs before acquiring lock
        if not handler_id or not handler_id.strip():
            raise ModelOnexError(
                message=(
                    "Handler ID cannot be empty or whitespace. "
                    "Provide a unique, descriptive identifier for the handler (e.g., 'user-event-handler')."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if handler is None or not callable(handler):
            raise ModelOnexError(
                message=(
                    f"Handler for '{handler_id}' must be callable (function or async function). "
                    f"Got {type(handler).__name__}. "
                    f"Expected signature: (envelope: ModelEventEnvelope[object], context: ProtocolHandlerContext) -> ModelHandlerOutput[object]"
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if not isinstance(category, EnumMessageCategory):
            raise ModelOnexError(
                message=(
                    f"Category must be EnumMessageCategory, got {type(category).__name__}. "
                    f"Valid categories: {', '.join(c.value for c in EnumMessageCategory)}"
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if not isinstance(node_kind, EnumNodeKind):
            raise ModelOnexError(
                message=(
                    f"node_kind must be EnumNodeKind, got {type(node_kind).__name__}. "
                    f"Valid node kinds: EFFECT, COMPUTE, REDUCER, ORCHESTRATOR"
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if node_kind == EnumNodeKind.RUNTIME_HOST:
            raise ModelOnexError(
                message=(
                    f"Cannot register handler '{handler_id}' with node_kind RUNTIME_HOST. "
                    "RUNTIME_HOST is for infrastructure nodes, not message handlers. "
                    "Use EFFECT, COMPUTE, REDUCER, or ORCHESTRATOR."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        with self._registration_lock:
            if self._frozen:
                raise ModelOnexError(
                    message=(
                        f"Cannot register handler '{handler_id}': MessageDispatchEngine is frozen. "
                        "Registration is not allowed after freeze() has been called. "
                        "Register all handlers before calling freeze()."
                    ),
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )

            if handler_id in self._handlers:
                existing_handler_info = self._handlers[handler_id]
                raise ModelOnexError(
                    message=(
                        f"Handler with ID '{handler_id}' is already registered. "
                        f"Existing handler: category={existing_handler_info.category.value}. "
                        f"Use a unique handler_id or unregister the existing handler first."
                    ),
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                )

            # Store handler entry
            entry = MessageDispatchEngine._HandlerEntry(
                handler_id=handler_id,
                handler=handler,
                category=category,
                message_types=message_types,
                node_kind=node_kind,
            )
            self._handlers[handler_id] = entry

            # Update category index
            self._handlers_by_category[category].append(handler_id)

            self._logger.debug(
                "Registered handler '%s' for category %s (message_types=%s)",
                handler_id,
                category,
                message_types if message_types else "all",
            )

    def freeze(self) -> None:
        """
        Freeze the engine to prevent further registration.

        Once frozen, any calls to register_route() or register_handler()
        will raise ModelOnexError with INVALID_STATE. This enforces the
        read-only-after-init pattern for thread safety.

        The freeze operation validates route-to-handler consistency:
        all routes must reference existing handlers.

        Raises:
            ModelOnexError: If any route references a non-existent handler
                (ITEM_NOT_REGISTERED)

        Example:
            >>> engine = MessageDispatchEngine()
            >>> engine.register_handler("h1", handler, EnumMessageCategory.EVENT)
            >>> engine.register_route(route)
            >>> engine.freeze()  # Validates and freezes
            >>> assert engine.is_frozen

        Note:
            This is a one-way operation. There is no unfreeze() method
            by design, as unfreezing would defeat thread-safety guarantees.

        .. versionadded:: 0.4.0
        """
        with self._registration_lock:
            if self._frozen:
                # Idempotent - already frozen
                return

            # Validate all routes reference existing handlers
            for route in self._routes.values():
                if route.handler_id not in self._handlers:
                    registered_handlers = sorted(self._handlers.keys())
                    raise ModelOnexError(
                        message=(
                            f"Route '{route.route_id}' references handler '{route.handler_id}' which is not registered. "
                            f"Registered handlers: {', '.join(registered_handlers) if registered_handlers else 'none'}. "
                            f"Register the handler using register_handler() before calling freeze()."
                        ),
                        error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                    )

            self._frozen = True
            self._logger.info(
                "MessageDispatchEngine frozen with %d routes and %d handlers",
                len(self._routes),
                len(self._handlers),
            )

    @property
    def is_frozen(self) -> bool:
        """
        Check if the engine is frozen.

        Returns:
            True if frozen and registration is disabled, False otherwise

        .. versionadded:: 0.4.0
        """
        return self._frozen

    def _increment_metric(self, key: MetricKey, value: int | float = 1) -> None:
        """
        Thread-safe increment of a metric value.

        Python's += operator is NOT atomic - it performs a read-modify-write
        sequence that can race with concurrent updates. This helper ensures
        all metrics updates are protected by a lock.

        Args:
            key: The metric key to increment (must be a valid MetricKey literal)
            value: The value to add (default: 1)

        Note:
            This method acquires _metrics_lock internally. Do not call while
            already holding the lock to avoid deadlock.

        .. versionadded:: 0.4.0
        """
        with self._metrics_lock:
            self._metrics[key] += value

    def _update_structured_metrics(
        self,
        duration_ms: float,
        success: bool,
        category: EnumMessageCategory | None = None,
        no_handler: bool = False,
        category_mismatch: bool = False,
        handler_error: bool = False,
        routes_matched: int = 0,
        topic: str | None = None,
        handler_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Thread-safe update of structured metrics.

        Atomically updates _structured_metrics using record_dispatch() while
        holding the metrics lock. This prevents data races during concurrent
        dispatch operations.

        Args:
            duration_ms: Dispatch duration in milliseconds (required)
            success: Whether dispatch succeeded (required)
            category: Message category
            no_handler: Whether no handler was found
            category_mismatch: Whether category mismatch occurred
            handler_error: Whether handler execution failed
            routes_matched: Number of routes matched
            topic: Topic being dispatched to
            handler_id: Handler ID (if applicable)
            error_message: Error message (if applicable)

        Note:
            This method acquires _metrics_lock internally. Do not call while
            already holding the lock to avoid deadlock.

        .. versionadded:: 0.4.0
        """
        with self._metrics_lock:
            self._structured_metrics = self._structured_metrics.record_dispatch(
                duration_ms=duration_ms,
                success=success,
                category=category,
                no_handler=no_handler,
                category_mismatch=category_mismatch,
                handler_error=handler_error,
                routes_matched=routes_matched,
                topic=topic,
                handler_id=handler_id,
                error_message=error_message,
            )

    def _update_handler_metrics(
        self,
        handler_id: str,
        duration_ms: float,
        success: bool,
        topic: str,
        error_message: str | None = None,
    ) -> None:
        """
        Thread-safe update of per-handler metrics.

        Atomically updates handler-specific metrics while holding the metrics
        lock. This prevents data races during concurrent handler executions.

        Args:
            handler_id: Handler's unique identifier
            duration_ms: Handler execution duration in milliseconds
            success: Whether handler execution succeeded
            topic: Topic being processed
            error_message: Error message if execution failed

        Note:
            This method acquires _metrics_lock internally. Do not call while
            already holding the lock to avoid deadlock.

        .. versionadded:: 0.4.0
        """
        with self._metrics_lock:
            # Get existing handler metrics
            existing_handler_metrics = self._structured_metrics.handler_metrics.get(
                handler_id
            )
            if existing_handler_metrics is None:
                existing_handler_metrics = ModelHandlerMetrics(handler_id=handler_id)

            # Record new execution
            new_handler_metrics = existing_handler_metrics.record_execution(
                duration_ms=duration_ms,
                success=success,
                topic=topic,
                error_message=error_message,
            )

            # Create updated metrics dict
            new_handler_metrics_dict = dict(self._structured_metrics.handler_metrics)
            new_handler_metrics_dict[handler_id] = new_handler_metrics

            # Atomically update structured metrics with new handler metrics
            # This creates a new ModelDispatchMetrics instance with updated handler data
            self._structured_metrics = ModelDispatchMetrics(
                total_dispatches=self._structured_metrics.total_dispatches,
                successful_dispatches=self._structured_metrics.successful_dispatches,
                failed_dispatches=self._structured_metrics.failed_dispatches,
                no_handler_count=self._structured_metrics.no_handler_count,
                category_mismatch_count=self._structured_metrics.category_mismatch_count,
                handler_execution_count=self._structured_metrics.handler_execution_count
                + 1,
                handler_error_count=(
                    self._structured_metrics.handler_error_count + (0 if success else 1)
                ),
                routes_matched_count=self._structured_metrics.routes_matched_count,
                total_latency_ms=self._structured_metrics.total_latency_ms,
                min_latency_ms=self._structured_metrics.min_latency_ms,
                max_latency_ms=self._structured_metrics.max_latency_ms,
                latency_histogram=self._structured_metrics.latency_histogram,
                handler_metrics=new_handler_metrics_dict,
                category_metrics=self._structured_metrics.category_metrics,
            )

    def _build_log_context(
        self,
        topic: str | None = None,
        category: EnumMessageCategory | None = None,
        message_type: str | None = None,
        handler_id: str | None = None,
        handler_count: int | None = None,
        duration_ms: float | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        dispatch_id: str | None = None,  # string-id-ok: log context field
        error_code: str | None = None,
    ) -> TypedDictLogContext:
        """
        Build structured log context dictionary.

        Args:
            topic: The topic being dispatched to.
            category: The message category.
            message_type: The message type.
            handler_id: Handler ID (or comma-separated list).
            handler_count: Number of handlers matched.
            duration_ms: Dispatch duration in milliseconds.
            correlation_id: Correlation ID from envelope.
            trace_id: Trace ID from envelope.
            dispatch_id: Dispatch ID for end-to-end request tracing.
            error_code: Error code if dispatch failed.

        Returns:
            Dictionary with non-None values for structured logging.
        """
        context: TypedDictLogContext = {}
        if topic is not None:
            context["topic"] = topic
        if category is not None:
            context["category"] = category.value
        if message_type is not None:
            context["message_type"] = message_type
        if handler_id is not None:
            context["handler_id"] = handler_id
        if handler_count is not None:
            context["handler_count"] = handler_count
        if duration_ms is not None:
            context["duration_ms"] = round(duration_ms, 3)
        if correlation_id is not None:
            context["correlation_id"] = correlation_id
        if trace_id is not None:
            context["trace_id"] = trace_id
        if dispatch_id is not None:
            context["dispatch_id"] = dispatch_id
        if error_code is not None:
            context["error_code"] = error_code
        return context

    async def dispatch(
        self,
        topic: str,
        envelope: ModelEventEnvelope[object],
    ) -> ModelDispatchResult:
        """
        Dispatch a message to matching handlers.

        Routes the message based on topic category and message type, executes
        all matching handlers, and collects their outputs.

        Dispatch Process:
            1. Parse topic to extract message category
            2. Validate envelope category matches topic category
            3. Get message type from envelope payload
            4. Find all matching handlers (by category + message type)
            5. Execute handlers (fan-out)
            6. Collect outputs and return result

        Args:
            topic: The topic the message was received on (e.g., "dev.user.events.v1")
            envelope: The message envelope to dispatch

        Returns:
            ModelDispatchResult with dispatch status, metrics, and handler outputs

        Raises:
            ModelOnexError: If engine is not frozen (INVALID_STATE)
            ModelOnexError: If topic is empty (INVALID_PARAMETER)
            ModelOnexError: If envelope is None (INVALID_PARAMETER)

        Example:
            >>> result = await engine.dispatch(
            ...     topic="dev.user.events.v1",
            ...     envelope=ModelEventEnvelope(payload=UserCreatedEvent(...)),
            ... )
            >>> if result.is_successful():
            ...     print(f"Dispatched to {result.output_count} handlers")

        Note:
            Handler exceptions are caught and reported in the result.
            The dispatch continues to other handlers even if one fails.

        .. versionadded:: 0.4.0
        """
        # Enforce freeze contract
        if not self._frozen:
            raise ModelOnexError(
                message=(
                    "dispatch() called before freeze(). "
                    "Registration MUST complete and freeze() MUST be called before dispatch. "
                    "This is required for thread safety. "
                    "Call engine.freeze() after all routes and handlers are registered."
                ),
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        # Validate inputs
        if not topic or not topic.strip():
            raise ModelOnexError(
                message=(
                    "Topic cannot be empty or whitespace. "
                    "Provide a valid topic name (e.g., 'dev.user-service.events.v1')."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if envelope is None:
            raise ModelOnexError(
                message=(
                    "Cannot dispatch None envelope. "
                    "Provide a valid ModelEventEnvelope instance with envelope_id, correlation_id, and payload."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Start timing
        start_time = time.perf_counter()
        dispatch_id = uuid4()
        started_at = datetime.now(UTC)

        # Extract correlation/trace/dispatch IDs for logging
        correlation_id_str = (
            str(envelope.correlation_id) if envelope.correlation_id else None
        )
        trace_id_str = str(envelope.trace_id) if envelope.trace_id else None
        dispatch_id_str = str(dispatch_id)

        # Update dispatch count (thread-safe via _increment_metric)
        self._increment_metric("dispatch_count")

        # Step 1: Parse topic to get category
        topic_category = EnumMessageCategory.from_topic(topic)
        if topic_category is None:
            self._increment_metric("dispatch_error_count")
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._increment_metric("total_latency_ms", duration_ms)

            # Update structured metrics (thread-safe)
            self._update_structured_metrics(
                duration_ms=duration_ms,
                success=False,
                category=None,
                no_handler=False,
                category_mismatch=False,
                topic=topic,
            )

            # Log error
            self._logger.error(
                "Dispatch failed: invalid topic category",
                extra=self._build_log_context(
                    topic=topic,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                    error_code="INVALID_TOPIC_CATEGORY",
                ),
            )

            return ModelDispatchResult(
                dispatch_id=dispatch_id,
                status=EnumDispatchStatus.INVALID_MESSAGE,
                topic=topic,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
                error_message=f"Cannot infer message category from topic '{topic}'. "
                "Topic must contain .events, .commands, or .intents segment.",
                error_code="INVALID_TOPIC_CATEGORY",
            )

        # Log dispatch start at INFO level
        self._logger.info(
            "Dispatch started",
            extra=self._build_log_context(
                topic=topic,
                category=topic_category,
                correlation_id=correlation_id_str,
                trace_id=trace_id_str,
                dispatch_id=dispatch_id_str,
            ),
        )

        # Step 2: Validate envelope category matches topic category
        envelope_category = envelope.infer_category()
        if envelope_category != topic_category:
            self._increment_metric("category_mismatch_count")
            self._increment_metric("dispatch_error_count")
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._increment_metric("total_latency_ms", duration_ms)

            # Update structured metrics (thread-safe)
            self._update_structured_metrics(
                duration_ms=duration_ms,
                success=False,
                category=topic_category,
                category_mismatch=True,
                topic=topic,
            )

            # Log warning
            self._logger.warning(
                "Dispatch failed: category mismatch (envelope=%s, topic=%s)",
                envelope_category,
                topic_category,
                extra=self._build_log_context(
                    topic=topic,
                    category=topic_category,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                    error_code="CATEGORY_MISMATCH",
                ),
            )

            return ModelDispatchResult(
                dispatch_id=dispatch_id,
                status=EnumDispatchStatus.INVALID_MESSAGE,
                topic=topic,
                message_category=topic_category,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
                error_message=(
                    f"Category mismatch: envelope category '{envelope_category}' does not match "
                    f"topic category '{topic_category}'. "
                    f"Envelope payload type: {type(envelope.payload).__name__}. "
                    f"Ensure the envelope category matches the topic's message category."
                ),
                error_code="CATEGORY_MISMATCH",
            )

        # Step 3: Get message type from payload
        message_type = type(envelope.payload).__name__

        # Step 4: Find matching handlers
        matching_handlers = self._find_matching_handlers(
            topic=topic,
            category=topic_category,
            message_type=message_type,
        )

        # Log routing decision at DEBUG level
        self._logger.debug(
            "Routing decision: %d handlers matched for message_type '%s'",
            len(matching_handlers),
            message_type,
            extra=self._build_log_context(
                topic=topic,
                category=topic_category,
                message_type=message_type,
                handler_count=len(matching_handlers),
                correlation_id=correlation_id_str,
                trace_id=trace_id_str,
                dispatch_id=dispatch_id_str,
            ),
        )

        if not matching_handlers:
            self._increment_metric("no_handler_count")
            self._increment_metric("dispatch_error_count")
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._increment_metric("total_latency_ms", duration_ms)

            # Update structured metrics (thread-safe)
            self._update_structured_metrics(
                duration_ms=duration_ms,
                success=False,
                category=topic_category,
                no_handler=True,
                topic=topic,
            )

            # Log warning
            self._logger.warning(
                "No handler found for category '%s' and message type '%s'",
                topic_category,
                message_type,
                extra=self._build_log_context(
                    topic=topic,
                    category=topic_category,
                    message_type=message_type,
                    handler_count=0,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                    error_code="NO_HANDLER_FOUND",
                ),
            )

            return ModelDispatchResult(
                dispatch_id=dispatch_id,
                status=EnumDispatchStatus.NO_HANDLER,
                topic=topic,
                message_category=topic_category,
                message_type=message_type,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
                error_message=f"No handler registered for category '{topic_category}' "
                f"and message type '{message_type}' matching topic '{topic}'.",
                error_code="NO_HANDLER_FOUND",
            )

        # Step 5: Execute handlers and collect outputs
        outputs: list[str] = []
        handler_outputs: list[ModelHandlerOutput[object]] = []
        handler_errors: list[str] = []
        executed_handler_ids: list[str] = []

        for handler_entry in matching_handlers:
            self._increment_metric("handler_execution_count")
            handler_start_time = time.perf_counter()

            # Log handler execution at DEBUG level
            self._logger.debug(
                "Executing handler '%s'",
                handler_entry.handler_id,
                extra=self._build_log_context(
                    topic=topic,
                    category=topic_category,
                    message_type=message_type,
                    handler_id=handler_entry.handler_id,
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                ),
            )

            try:
                result = await self._execute_handler(
                    handler_entry, envelope, dispatch_id
                )
                handler_duration_ms = (time.perf_counter() - handler_start_time) * 1000
                executed_handler_ids.append(handler_entry.handler_id)

                # Update per-handler metrics (thread-safe)
                self._update_handler_metrics(
                    handler_id=handler_entry.handler_id,
                    duration_ms=handler_duration_ms,
                    success=True,
                    topic=topic,
                )

                # Log handler completion at DEBUG level
                self._logger.debug(
                    "Handler '%s' completed successfully in %.2f ms",
                    handler_entry.handler_id,
                    handler_duration_ms,
                    extra=self._build_log_context(
                        topic=topic,
                        category=topic_category,
                        message_type=message_type,
                        handler_id=handler_entry.handler_id,
                        duration_ms=handler_duration_ms,
                        correlation_id=correlation_id_str,
                        trace_id=trace_id_str,
                        dispatch_id=dispatch_id_str,
                    ),
                )

                # Collect handler outputs for causality-correct publishing
                # Handlers now return ModelHandlerOutput (OMN-941)
                if isinstance(result, ModelHandlerOutput):
                    handler_outputs.append(result)
                    # Track output count in the string outputs list for logging
                    output_count = result.output_count()
                    if output_count > 0:
                        outputs.append(
                            f"<{output_count} outputs from {handler_entry.handler_id}>"
                        )
                # Handle string or list returns (topic strings)
                elif isinstance(result, str) and result:
                    outputs.append(result)
                elif isinstance(result, list):
                    outputs.extend(str(r) for r in result if r)
            except (GeneratorExit, KeyboardInterrupt, SystemExit):
                # Never catch cancellation/exit signals
                raise
            except asyncio.CancelledError:
                # Never suppress async cancellation
                raise
            # boundary-ok: handler errors captured for metrics and logging, continue dispatch loop
            except Exception as e:
                handler_duration_ms = (time.perf_counter() - handler_start_time) * 1000
                self._increment_metric("handler_error_count")
                error_msg = f"Handler '{handler_entry.handler_id}' failed: {type(e).__name__}: {e}"
                handler_errors.append(error_msg)

                # Update per-handler metrics with error (thread-safe)
                self._update_handler_metrics(
                    handler_id=handler_entry.handler_id,
                    duration_ms=handler_duration_ms,
                    success=False,
                    topic=topic,
                    error_message=str(e),
                )

                # Log error
                self._logger.exception(
                    "Handler '%s' failed: %s",
                    handler_entry.handler_id,
                    e,
                    extra=self._build_log_context(
                        topic=topic,
                        category=topic_category,
                        message_type=message_type,
                        handler_id=handler_entry.handler_id,
                        duration_ms=handler_duration_ms,
                        correlation_id=correlation_id_str,
                        trace_id=trace_id_str,
                        dispatch_id=dispatch_id_str,
                        error_code="HANDLER_EXCEPTION",
                    ),
                )

        # Step 5.5: Publish handler outputs in causality-correct order (OMN-941)
        # Order: events -> projections -> intents
        # Note: Actual publishing requires an event_bus to be provided via dispatch_with_event_bus()
        # For now, we just count the outputs - publishing will be done by dispatch_with_event_bus()
        total_handler_output_count = await self._publish_outputs_in_order(
            handler_outputs=handler_outputs,
            event_bus=None,  # No event_bus provided in basic dispatch()
        )

        if total_handler_output_count > 0:
            self._logger.debug(
                "Collected %d handler outputs for causality-correct publishing",
                total_handler_output_count,
                extra=self._build_log_context(
                    topic=topic,
                    category=topic_category,
                    message_type=message_type,
                    handler_count=len(handler_outputs),
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                ),
            )

        # Step 6: Build result
        duration_ms = (time.perf_counter() - start_time) * 1000
        self._increment_metric("total_latency_ms", duration_ms)
        self._increment_metric("routes_matched_count", len(matching_handlers))

        # Determine final status
        if handler_errors:
            if executed_handler_ids:
                # Partial success - some handlers executed
                status = EnumDispatchStatus.HANDLER_ERROR
                self._increment_metric("dispatch_error_count")
            else:
                # Total failure - no handlers executed
                status = EnumDispatchStatus.HANDLER_ERROR
                self._increment_metric("dispatch_error_count")
        else:
            status = EnumDispatchStatus.SUCCESS
            self._increment_metric("dispatch_success_count")

        # Update structured metrics with final dispatch result (thread-safe)
        self._update_structured_metrics(
            duration_ms=duration_ms,
            success=status == EnumDispatchStatus.SUCCESS,
            category=topic_category,
            handler_id=executed_handler_ids[0] if executed_handler_ids else None,
            handler_error=len(handler_errors) > 0,
            routes_matched=len(matching_handlers),
            topic=topic,
            error_message=handler_errors[0] if handler_errors else None,
        )

        # Find route ID that matched (first matching route for logging)
        matched_route_id: str | None = None
        for route in self._routes.values():
            if route.matches(topic, topic_category, message_type):
                matched_route_id = route.route_id
                break

        # Log dispatch completion at INFO level
        handler_ids_str = (
            ", ".join(executed_handler_ids) if executed_handler_ids else None
        )
        if status == EnumDispatchStatus.SUCCESS:
            self._logger.info(
                "Dispatch completed successfully",
                extra=self._build_log_context(
                    topic=topic,
                    category=topic_category,
                    message_type=message_type,
                    handler_id=handler_ids_str,
                    handler_count=len(executed_handler_ids),
                    duration_ms=duration_ms,
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                ),
            )
        else:
            self._logger.error(
                "Dispatch completed with errors",
                extra=self._build_log_context(
                    topic=topic,
                    category=topic_category,
                    message_type=message_type,
                    handler_id=handler_ids_str,
                    handler_count=len(matching_handlers),
                    duration_ms=duration_ms,
                    correlation_id=correlation_id_str,
                    trace_id=trace_id_str,
                    dispatch_id=dispatch_id_str,
                    error_code="HANDLER_EXECUTION_ERROR",
                ),
            )

        return ModelDispatchResult(
            dispatch_id=dispatch_id,
            status=status,
            route_id=matched_route_id,
            handler_id=handler_ids_str,
            topic=topic,
            message_category=topic_category,
            message_type=message_type,
            duration_ms=duration_ms,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            outputs=outputs if outputs else None,
            output_count=len(outputs),
            error_message="; ".join(handler_errors) if handler_errors else None,
            error_code="HANDLER_EXECUTION_ERROR" if handler_errors else None,
            correlation_id=envelope.correlation_id,
            trace_id=envelope.trace_id,
            span_id=envelope.span_id,
        )

    def _find_matching_handlers(
        self,
        topic: str,
        category: EnumMessageCategory,
        message_type: str,
    ) -> list[MessageDispatchEngine._HandlerEntry]:
        """
        Find all handlers that match the given criteria.

        Matching is done in two phases:
        1. Find routes that match topic pattern and category
        2. Find handlers for those routes that accept the message type

        Args:
            topic: The topic to match
            category: The message category
            message_type: The specific message type

        Returns:
            List of matching handler entries (may be empty)
        """
        matching_handlers: list[MessageDispatchEngine._HandlerEntry] = []
        seen_handler_ids: set[str] = set()

        # Find all routes that match this topic and category
        for route in self._routes.values():
            if not route.enabled:
                continue
            if not route.matches_topic(topic):
                continue
            if route.message_category != category:
                continue
            # Route-level message type filter (if specified)
            if route.message_type is not None and route.message_type != message_type:
                continue

            # Get the handler for this route
            handler_id = route.handler_id
            if handler_id in seen_handler_ids:
                # Avoid duplicate handler execution
                continue

            entry = self._handlers.get(handler_id)
            if entry is None:
                # Handler not found (should have been caught at freeze)
                self._logger.warning(
                    "Route '%s' references missing handler '%s'",
                    route.route_id,
                    handler_id,
                )
                continue

            # Check handler-level message type filter
            if (
                entry.message_types is not None
                and message_type not in entry.message_types
            ):
                continue

            matching_handlers.append(entry)
            seen_handler_ids.add(handler_id)

        return matching_handlers

    def _build_handler_context(
        self,
        entry: MessageDispatchEngine._HandlerEntry,
        envelope: ModelEventEnvelope[object],
        dispatch_id: UUID | None = None,
    ) -> ProtocolHandlerContext:
        """
        Build the appropriate context model for a handler based on its node_kind.

        Context type selection:
            - EFFECT: ModelEffectContext (with `now`, `retry_attempt`)
            - COMPUTE: ModelComputeContext (no `now` - pure function)
            - REDUCER: ModelReducerContext (no `now` - pure function)
            - ORCHESTRATOR: ModelOrchestratorContext (with `now`)

        The context carries causality tracking fields from the envelope:
            - correlation_id: Request tracing across services
            - envelope_id: Links handler invocation to triggering event
            - dispatch_id: Identifies the dispatch operation for correlation
            - trace_id/span_id: Optional OpenTelemetry integration

        Args:
            entry: Handler entry with node_kind
            envelope: Source envelope for correlation/trace IDs
            dispatch_id: Optional dispatch operation ID for request tracing.
                Uniquely identifies a single dispatch() call. All handlers
                in the same dispatch share this ID.

        Returns:
            Appropriate context model for the handler's node_kind.
            All context models implement ProtocolHandlerContext.

        Raises:
            ModelOnexError: If node_kind is RUNTIME_HOST (should not happen
                as registration rejects RUNTIME_HOST)
        """
        # Extract IDs from envelope
        # correlation_id is required in context, generate if missing
        correlation_id = envelope.correlation_id
        if correlation_id is None:
            self._logger.warning(
                "Missing correlation_id in envelope, generating fallback UUID "
                "(envelope_id=%s). This may indicate an upstream issue.",
                envelope.envelope_id,
            )
            correlation_id = uuid4()

        envelope_id = envelope.envelope_id
        trace_id = envelope.trace_id
        span_id = envelope.span_id

        node_kind = entry.node_kind

        # Ensure retry_count is non-negative (ModelEffectContext.retry_attempt
        # has ge=0 constraint). Protect against corrupted envelope data.
        retry_attempt = envelope.retry_count
        if retry_attempt < 0:
            self._logger.warning(
                "Envelope has negative retry_count=%d (envelope_id=%s), clamping to 0. "
                "This may indicate data corruption.",
                retry_attempt,
                envelope.envelope_id,
            )
            retry_attempt = 0

        # Build context based on node_kind
        # Use single return point for consistent protocol assertion
        context: ProtocolHandlerContext

        if node_kind == EnumNodeKind.EFFECT:
            context = ModelEffectContext(
                correlation_id=correlation_id,
                envelope_id=envelope_id,
                dispatch_id=dispatch_id,
                trace_id=trace_id,
                span_id=span_id,
                retry_attempt=retry_attempt,
            )

        elif node_kind == EnumNodeKind.COMPUTE:
            context = ModelComputeContext(
                correlation_id=correlation_id,
                envelope_id=envelope_id,
                dispatch_id=dispatch_id,
                trace_id=trace_id,
                span_id=span_id,
            )

        elif node_kind == EnumNodeKind.REDUCER:
            context = ModelReducerContext(
                correlation_id=correlation_id,
                envelope_id=envelope_id,
                dispatch_id=dispatch_id,
                trace_id=trace_id,
                span_id=span_id,
            )

        elif node_kind == EnumNodeKind.ORCHESTRATOR:
            context = ModelOrchestratorContext(
                correlation_id=correlation_id,
                envelope_id=envelope_id,
                dispatch_id=dispatch_id,
                trace_id=trace_id,
                span_id=span_id,
            )

        else:
            # RUNTIME_HOST or unknown - should not reach here
            raise ModelOnexError(
                message=f"Cannot build context for node_kind {node_kind}. "
                "Only EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR are valid.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Runtime assertion for protocol compliance during development
        # Only runs when __debug__ is True (i.e., not with python -O)
        if __debug__:
            assert isinstance(context, ProtocolHandlerContext), (
                f"Context {type(context).__name__} does not implement "
                f"ProtocolHandlerContext"
            )

        return context

    async def _execute_handler(
        self,
        entry: MessageDispatchEngine._HandlerEntry,
        envelope: ModelEventEnvelope[object],
        dispatch_id: UUID | None = None,
    ) -> ModelHandlerOutput[object] | str | list[object]:
        """
        Execute a handler (sync or async) with context injection.

        Builds the appropriate context based on the handler's node_kind
        and invokes the handler with both envelope and context.

        Args:
            entry: The handler entry containing the callable and node_kind
            envelope: The message envelope to process
            dispatch_id: Optional dispatch operation ID for request tracing.
                Uniquely identifies a single dispatch() call.

        Returns:
            Handler result (any type)

        Raises:
            Any exception raised by the handler
        """
        handler = entry.handler

        # Build context from envelope + handler's node_kind + dispatch_id
        context = self._build_handler_context(entry, envelope, dispatch_id)

        # Check if handler is async
        if inspect.iscoroutinefunction(handler):
            result: HandlerReturnType = await handler(envelope, context)
            return result
        else:
            # Sync handler - run in executor to avoid blocking
            # Cast to SyncHandlerFunc for type narrowing (runtime check above
            # guarantees this is not an async function)
            sync_handler = cast(SyncHandlerFunc, handler)
            loop = asyncio.get_running_loop()
            sync_result: HandlerReturnType = await loop.run_in_executor(
                None, sync_handler, envelope, context
            )
            return sync_result

    async def _publish_outputs_in_order(
        self,
        handler_outputs: Sequence[ModelHandlerOutput[object]],
        event_bus: ProtocolEventBus | None = None,
        publish_intents: bool = False,
    ) -> int:
        """
        Publish handler outputs in causality-correct order.

        Publishing Order (CRITICAL for causality):
            1. events[] - Facts that happened (cause)
            2. projections[] - Derived state from events
            3. intents[] - Desired future effects (only if publish_intents=True)

        Within each category, handler-returned order is preserved.

        This ordering ensures that:
            - Events (facts) are always published first
            - Projections (derived state) follow events
            - Intents (requested side effects) are published last,
              ensuring they cannot be processed before their causal events

        Intent Publishing Policy (OMN-941):
            Intents are runtime-internal by default and are NOT published to
            the event bus unless publish_intents=True is explicitly set.

            Rationale:
            - If you publish intents externally, you are making them part of
              your public protocol surface - that is a commitment, not "just
              observability"
            - Intents should go to a trace/ledger system for debugging instead
              of the main event bus
            - Only enable publish_intents=True if you have explicit external
              consumers that need to react to intents

        Args:
            handler_outputs: Sequence of ModelHandlerOutput from handlers.
                Order is preserved within each category.
            event_bus: Optional event bus for publishing. If None, outputs
                are collected and counted but not published.
            publish_intents: Whether to publish intents to the event bus.
                Defaults to False (runtime-internal only). Set to True only
                if you have explicit external consumers for intents. See
                OMN-941 for architectural rationale.

        Returns:
            Total number of items published (or would be published if no event_bus).

        Example:
            >>> # Handler 1 returns: events=[E1], intents=[I1]
            >>> # Handler 2 returns: events=[E2], projections=[P1]
            >>> # Default (publish_intents=False): E1, E2, P1 (intents NOT published)
            >>> count = await engine._publish_outputs_in_order(
            ...     handler_outputs=[output1, output2],
            ...     event_bus=my_event_bus,
            ... )
            >>> assert count == 3  # Intents not published by default
            >>>
            >>> # With publish_intents=True: E1, E2, P1, I1
            >>> count = await engine._publish_outputs_in_order(
            ...     handler_outputs=[output1, output2],
            ...     event_bus=my_event_bus,
            ...     publish_intents=True,
            ... )
            >>> assert count == 4  # All outputs including intents

        Note:
            Handler outputs are aggregated across all handlers in a fan-out
            scenario. The causality order is maintained globally, not per-handler.

        .. versionadded:: 0.4.0
        """
        published_count = 0

        # 1. Collect all events FIRST (facts that happened)
        # Preserves handler-returned order within category
        all_events: list[object] = [
            e for output in handler_outputs for e in output.events
        ]

        # 2. Collect all projections (derived state)
        all_projections: list[object] = [
            p for output in handler_outputs for p in output.projections
        ]

        # 3. Collect all intents LAST (desired future effects)
        all_intents: list[object] = [
            i for output in handler_outputs for i in output.intents
        ]

        # Publish in causality-correct order
        if event_bus:
            # Publish events first (causes)
            for event in all_events:
                # Events are ModelEventEnvelope instances - serialize and publish
                # The event_bus.publish expects topic, key, value, headers
                # For now, we assume events have a topic attribute or we use a default
                if hasattr(event, "model_dump_json"):
                    value = event.model_dump_json().encode("utf-8")
                else:
                    value = str(event).encode("utf-8")

                # Extract topic from event if available
                topic = getattr(event, "topic", "default.events")
                await event_bus.publish(
                    topic=topic, key=None, value=value, headers=None
                )
                published_count += 1

            # Publish projections second (derived state)
            for projection in all_projections:
                if hasattr(projection, "model_dump_json"):
                    value = projection.model_dump_json().encode("utf-8")
                else:
                    value = str(projection).encode("utf-8")

                topic = getattr(projection, "topic", "default.projections")
                await event_bus.publish(
                    topic=topic, key=None, value=value, headers=None
                )
                published_count += 1

            # Publish intents last (future effects) - ONLY if publish_intents=True
            # By default, intents are runtime-internal and NOT published (OMN-941)
            if publish_intents:
                for intent in all_intents:
                    if hasattr(intent, "model_dump_json"):
                        value = intent.model_dump_json().encode("utf-8")
                    else:
                        value = str(intent).encode("utf-8")

                    topic = getattr(intent, "topic", "default.intents")
                    await event_bus.publish(
                        topic=topic, key=None, value=value, headers=None
                    )
                    published_count += 1
        else:
            # Just count if no event_bus provided
            # Include intents in count only if publish_intents=True
            intent_count = len(all_intents) if publish_intents else 0
            published_count = len(all_events) + len(all_projections) + intent_count

        return published_count

    def get_metrics(self) -> TypedDictLegacyDispatchMetrics:
        """
        Get dispatch metrics for observability (legacy format).

        Returns a snapshot of current metrics including:
        - dispatch_count: Total number of dispatch calls
        - dispatch_success_count: Successful dispatches
        - dispatch_error_count: Failed dispatches
        - total_latency_ms: Cumulative latency in milliseconds
        - handler_execution_count: Total handler executions
        - handler_error_count: Handler execution failures
        - routes_matched_count: Total route matches
        - no_handler_count: Dispatches with no matching handler
        - category_mismatch_count: Category validation failures

        Returns:
            Dictionary with metrics (copy of internal state)

        Example:
            >>> metrics = engine.get_metrics()
            >>> print(f"Success rate: {metrics['dispatch_success_count'] / metrics['dispatch_count']:.1%}")

        Note:
            Returns a copy to prevent external modification.
            For high-frequency monitoring, consider caching the result.
            For structured metrics, use get_structured_metrics() instead.
            Thread-safe: Protected by metrics lock to prevent torn reads.

        .. versionadded:: 0.4.0
        """
        # Thread-safe snapshot of metrics
        # Must hold lock to prevent torn reads during concurrent updates
        with self._metrics_lock:
            return TypedDictLegacyDispatchMetrics(
                dispatch_count=self._metrics["dispatch_count"],
                dispatch_success_count=self._metrics["dispatch_success_count"],
                dispatch_error_count=self._metrics["dispatch_error_count"],
                total_latency_ms=self._metrics["total_latency_ms"],
                handler_execution_count=self._metrics["handler_execution_count"],
                handler_error_count=self._metrics["handler_error_count"],
                routes_matched_count=self._metrics["routes_matched_count"],
                no_handler_count=self._metrics["no_handler_count"],
                category_mismatch_count=self._metrics["category_mismatch_count"],
            )

    def get_structured_metrics(self) -> ModelDispatchMetrics:
        """
        Get structured dispatch metrics using Pydantic model.

        Returns a comprehensive metrics model including:
        - Dispatch counts and success/error rates
        - Latency statistics (average, min, max)
        - Latency histogram for distribution analysis
        - Per-handler metrics breakdown
        - Per-category metrics breakdown

        Returns:
            ModelDispatchMetrics with all observability data

        Example:
            >>> metrics = engine.get_structured_metrics()
            >>> print(f"Success rate: {metrics.success_rate:.1%}")
            >>> print(f"Avg latency: {metrics.avg_latency_ms:.2f} ms")
            >>> for handler_id, handler_metrics in metrics.handler_metrics.items():
            ...     print(f"Handler {handler_id}: {handler_metrics.execution_count} executions")

        Note:
            Thread-safe: Returns a snapshot of metrics at the time of call.
            Pydantic models are immutable after creation, so the returned
            instance is safe to use across threads.

        .. versionadded:: 0.4.0
        """
        with self._metrics_lock:
            return self._structured_metrics

    def reset_metrics(self) -> None:
        """
        Reset all metrics to initial state.

        Useful for testing or when starting a new monitoring period.
        Resets both legacy dict-based metrics and structured metrics.

        Example:
            >>> engine.reset_metrics()
            >>> assert engine.get_metrics()["dispatch_count"] == 0
            >>> assert engine.get_structured_metrics().total_dispatches == 0

        Note:
            Thread-safe: Protected by metrics lock to prevent races during reset.

        .. versionadded:: 0.4.0
        """
        with self._metrics_lock:
            self._metrics = {
                "dispatch_count": 0,
                "dispatch_success_count": 0,
                "dispatch_error_count": 0,
                "total_latency_ms": 0.0,
                "handler_execution_count": 0,
                "handler_error_count": 0,
                "routes_matched_count": 0,
                "no_handler_count": 0,
                "category_mismatch_count": 0,
            }
            self._structured_metrics = ModelDispatchMetrics()
        self._logger.debug("Metrics reset to initial state")

    def get_handler_metrics(self, handler_id: str) -> ModelHandlerMetrics | None:
        """
        Get metrics for a specific handler.

        Args:
            handler_id: The handler's unique identifier.

        Returns:
            ModelHandlerMetrics for the handler, or None if no metrics recorded.

        Example:
            >>> metrics = engine.get_handler_metrics("user-event-handler")
            >>> if metrics:
            ...     print(f"Executions: {metrics.execution_count}")
            ...     print(f"Error rate: {metrics.error_rate:.1%}")

        Note:
            Thread-safe: Protected by metrics lock to prevent races during read.

        .. versionadded:: 0.4.0
        """
        with self._metrics_lock:
            return self._structured_metrics.handler_metrics.get(handler_id)

    @property
    def route_count(self) -> int:
        """Get the number of registered routes."""
        return len(self._routes)

    @property
    def handler_count(self) -> int:
        """Get the number of registered handlers."""
        return len(self._handlers)

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"MessageDispatchEngine[routes={len(self._routes)}, "
            f"handlers={len(self._handlers)}, frozen={self._frozen}]"
        )

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        route_ids = list(self._routes.keys())[:10]
        handler_ids = list(self._handlers.keys())[:10]

        route_repr = (
            repr(route_ids)
            if len(self._routes) <= 10
            else f"<{len(self._routes)} routes>"
        )
        handler_repr = (
            repr(handler_ids)
            if len(self._handlers) <= 10
            else f"<{len(self._handlers)} handlers>"
        )

        return (
            f"MessageDispatchEngine("
            f"routes={route_repr}, "
            f"handlers={handler_repr}, "
            f"frozen={self._frozen})"
        )
