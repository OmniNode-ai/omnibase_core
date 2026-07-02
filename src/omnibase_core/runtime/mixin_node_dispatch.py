# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Node-owned dispatch-selection seam (OMN-12549, epic OMN-12525).

``MixinNodeDispatch`` is the core-side, node-owned successor to the routing that
today lives inside :class:`omnibase_infra.runtime.message_dispatch_engine.MessageDispatchEngine`.
It ports the engine's *selection* semantics — the ``_find_matching_dispatchers``
algorithm plus the surrounding ``dispatch()`` category/message-type derivation —
using **core-only symbols** so orchestrator and effect nodes can own dispatch
selection without depending on ``omnibase_infra``.

Scope (design D4 / OMN-12549):
    This mixin performs **selection only**. It resolves which registered
    dispatchers a ``(topic, envelope)`` pair routes to and returns a
    :class:`~omnibase_core.models.dispatch.model_dispatch_result.ModelDispatchResult`
    whose equivalence tuple

        (status, ordered dispatcher_ids, message_category, message_type, dlq_topic)

    matches the live engine's for the same input. Handler *execution*, metrics,
    binding resolution, and context injection remain the runtime's job and are
    intentionally out of scope here — the engine stays live (no behavior change)
    until the S5 cutover retires it.

Parity contract (OMN-12548 S0 gate):
    ``tests/integration/runtime/test_dispatch_selection_parity.py`` in
    ``omnibase_infra`` drives the same probe corpus through both this mixin and
    the engine behind ``ProtocolDispatchEngine`` and asserts tuple equality. The
    only engine behavior this mixin cannot reproduce with core-only symbols is
    DLQ-topic derivation (``omnibase_infra.event_bus.topic_constants``); that is
    injected as a callable via :meth:`set_dlq_topic_deriver`, keeping the mixin
    infra-free while preserving the ``dlq_topic`` element of the tuple.

Usage as a node mixin:
    ``__init__`` is cooperative (``super().__init__(**kwargs)``) so the mixin
    slots into a node MRO exactly like :class:`MixinHandlerRouting`. State is
    lazily materialized, so a node that never registers routes carries no
    dispatch table and pays nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.dispatch.model_dispatch_result import ModelDispatchResult
from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.models.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.enums.enum_node_kind import EnumNodeKind
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

__all__ = ["MixinNodeDispatch"]

# A dispatcher is any callable the node registers; selection never invokes it, so
# its precise signature is irrelevant to this mixin (execution lives elsewhere).
_DispatcherCallable = Callable[..., object]

# Injected DLQ-topic deriver: ``(event_type | None, original_topic) -> dlq_topic | None``.
# The infra runtime injects ``message_dispatch_engine._derive_dlq_topic`` so the
# NO_DISPATCHER tuple's ``dlq_topic`` element matches the live engine. When absent,
# derivation yields ``None`` (the mixin never imports infra topic constants).
DlqTopicDeriver = Callable[[str | None, str], str | None]


class _NodeDispatchEntry:
    """Selection metadata for one registered dispatcher (core-only mirror of the
    engine's ``DispatchEntryInternal``, minus the execution-only fields)."""

    __slots__ = (
        "category",
        "dispatcher",
        "dispatcher_id",
        "message_types",
        "node_kind",
        "payload_type_matcher",
    )

    def __init__(
        self,
        *,
        dispatcher_id: str,
        dispatcher: _DispatcherCallable,
        category: EnumMessageCategory,
        message_types: set[str] | None,
        node_kind: EnumNodeKind | None,
        payload_type_matcher: Callable[[object], bool] | None,
    ) -> None:
        self.dispatcher_id = dispatcher_id
        self.dispatcher = dispatcher
        self.category = category
        self.message_types = message_types  # None means "all message types"
        self.node_kind = node_kind
        # None means "not type-scoped" — legacy string-only matching applies.
        self.payload_type_matcher = payload_type_matcher


class _NodeDispatchState:
    """Per-instance selection table. Materialized lazily so an unused mixin is inert."""

    __slots__ = ("dispatchers", "dlq_topic_deriver", "frozen", "routes")

    def __init__(self) -> None:
        self.routes: dict[str, ModelDispatchRoute] = {}
        self.dispatchers: dict[str, _NodeDispatchEntry] = {}
        self.frozen: bool = False
        self.dlq_topic_deriver: DlqTopicDeriver | None = None


class MixinNodeDispatch:
    """Contract-table dispatch **selection** owned by the node (OMN-12549).

    Public surface mirrors the engine's registration + dispatch API so the same
    probe corpus can drive both behind ``ProtocolDispatchEngine``:
    :meth:`register_dispatcher`, :meth:`register_route`, :meth:`freeze`, and the
    async :meth:`dispatch`. Selection is stateless and deterministic: the same
    frozen table and input always yield the same dispatcher selection and tuple.
    """

    # Class-level annotation only (no assignment) so mypy sees the attribute while
    # the value is materialized lazily via ``_state``. Mirrors MixinHandlerRouting.
    _node_dispatch_state: _NodeDispatchState

    def __init__(self, **kwargs: object) -> None:
        """Cooperative MRO init. State is created here for standalone use and is
        also (re)materialized lazily so node subclasses that skip kwargs are safe."""
        super().__init__(**kwargs)
        self._node_dispatch_state = _NodeDispatchState()

    # -- internal state access ------------------------------------------------

    def _state(self) -> _NodeDispatchState:
        """Return the selection table, materializing it on first use.

        Lazy creation keeps the mixin inert when a node never registers routes and
        tolerates instantiation paths that bypass ``__init__`` (defensive)."""
        state = getattr(self, "_node_dispatch_state", None)
        if state is None:
            state = _NodeDispatchState()
            self._node_dispatch_state = state
        return state

    # -- configuration --------------------------------------------------------

    def set_dlq_topic_deriver(self, deriver: DlqTopicDeriver | None) -> None:
        """Inject the DLQ-topic deriver used on the NO_DISPATCHER path.

        The mixin stays infra-free by never importing DLQ topic constants; the
        runtime injects ``message_dispatch_engine._derive_dlq_topic`` so the
        ``dlq_topic`` element of the selection tuple matches the live engine.
        """
        self._state().dlq_topic_deriver = deriver

    # -- registration ---------------------------------------------------------

    def register_route(self, route: ModelDispatchRoute) -> None:
        """Register a routing rule (duplicate ``route_id`` is rejected)."""
        if route is None:
            raise ModelOnexError(
                message="Cannot register None route. ModelDispatchRoute is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        state = self._state()
        if state.frozen:
            raise ModelOnexError(
                message="Cannot register route: MixinNodeDispatch is frozen. "
                "Registration is not allowed after freeze().",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        if route.route_id in state.routes:
            raise ModelOnexError(
                message=f"Route with ID '{route.route_id}' is already registered.",
                error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            )
        state.routes[route.route_id] = route

    def register_dispatcher(
        self,
        dispatcher_id: str,
        dispatcher: _DispatcherCallable,
        category: EnumMessageCategory,
        message_types: set[str] | None = None,
        node_kind: EnumNodeKind | None = None,
        payload_type_matcher: Callable[[object], bool] | None = None,
    ) -> None:
        """Register a dispatcher (duplicate ``dispatcher_id`` is rejected).

        ``payload_type_matcher`` makes the dispatcher type-scoped: it is selected
        only when the matcher accepts the message payload (OMN-12416), so a
        multi-handler contract routes each message to the single handler whose
        declared ``event_model`` matches instead of fanning out to every sibling.
        ``node_kind`` is retained for parity with the engine registration surface
        but does not influence selection (it drives execution-time context only).
        """
        if not dispatcher_id or not dispatcher_id.strip():
            raise ModelOnexError(
                message="Dispatcher ID cannot be empty or whitespace.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        if dispatcher is None or not callable(dispatcher):
            raise ModelOnexError(
                message=f"Dispatcher for '{dispatcher_id}' must be callable. "
                f"Got {type(dispatcher).__name__}.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        state = self._state()
        if state.frozen:
            raise ModelOnexError(
                message="Cannot register dispatcher: MixinNodeDispatch is frozen. "
                "Registration is not allowed after freeze().",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        if dispatcher_id in state.dispatchers:
            raise ModelOnexError(
                message=f"Dispatcher with ID '{dispatcher_id}' is already registered.",
                error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            )
        state.dispatchers[dispatcher_id] = _NodeDispatchEntry(
            dispatcher_id=dispatcher_id,
            dispatcher=dispatcher,
            category=category,
            message_types=message_types,
            node_kind=node_kind,
            payload_type_matcher=payload_type_matcher,
        )

    def freeze(self) -> None:
        """Freeze the table for dispatch. Validates every route references a
        registered dispatcher; idempotent once frozen."""
        state = self._state()
        if state.frozen:
            return
        for route in state.routes.values():
            rid = route.handler_id
            if rid not in state.dispatchers:
                raise ModelOnexError(
                    message=f"Route '{route.route_id}' references dispatcher "
                    f"'{rid}' which is not registered.",
                    error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                )
        state.frozen = True

    @property
    def is_frozen(self) -> bool:
        """True once :meth:`freeze` has been called."""
        return self._state().frozen

    # -- selection ------------------------------------------------------------

    def _find_matching_dispatchers(
        self,
        *,
        topic: str,
        category: EnumMessageCategory,
        message_type: str,
        payload: object | None,
    ) -> list[_NodeDispatchEntry]:
        """Port of the engine's ``_find_matching_dispatchers`` (selection only).

        Iterates routes in registration (insertion) order — the fan-out order the
        tuple pins — and keeps each route's dispatcher when: the route is enabled
        and matches the topic + category (+ optional route message-type filter),
        the dispatcher's own message-type filter admits ``message_type``, and, for
        type-scoped dispatchers, the payload matches the declared event_model.
        """
        matching: list[_NodeDispatchEntry] = []
        seen: set[str] = set()
        state = self._state()
        for route in state.routes.values():
            if not route.enabled:
                continue
            if not route.matches_topic(topic):
                continue
            if route.message_category != category:
                continue
            if route.message_type is not None and route.message_type != message_type:
                continue
            dispatcher_id = route.handler_id
            if dispatcher_id in seen:
                continue
            entry = state.dispatchers.get(dispatcher_id)
            if entry is None:
                # Should be impossible after freeze() validation; skip defensively.
                continue
            if (
                entry.message_types is not None
                and message_type not in entry.message_types
            ):
                continue
            if (
                payload is not None
                and entry.payload_type_matcher is not None
                and not self._payload_matches(entry, payload)
            ):
                continue
            matching.append(entry)
            seen.add(dispatcher_id)
        return matching

    @staticmethod
    def _payload_matches(entry: _NodeDispatchEntry, payload: object) -> bool:
        """True when ``payload`` matches a type-scoped dispatcher's event_model.

        A raising matcher means "not my type" (never selected), mirroring the
        engine — a malformed/wrong-type payload never selects a type-scoped
        dispatcher. Callers only invoke this when a matcher is present.
        """
        matcher = entry.payload_type_matcher
        if matcher is None:
            return True
        try:
            return bool(matcher(payload))
        except Exception:  # noqa: BLE001 — a raising matcher means "not my type"
            return False

    async def dispatch(
        self,
        topic: str,
        envelope: ModelEventEnvelope[object],
    ) -> ModelDispatchResult:
        """Select the dispatchers a ``(topic, envelope)`` routes to.

        Returns a :class:`ModelDispatchResult` whose equivalence tuple matches the
        live engine's for the same input:

        * ``INVALID_MESSAGE`` when the topic yields no message category;
        * ``NO_DISPATCHER`` (with an injected ``dlq_topic``) when nothing matches;
        * ``SUCCESS`` with the ordered matched dispatcher ids otherwise.

        Selection performs no handler execution; ``dispatcher_id`` carries the
        comma-joined ordered selection, exactly as the engine records the executed
        fan-out for an inert (side-effect-free) dispatcher.
        """
        state = self._state()
        if not state.frozen:
            raise ModelOnexError(
                message="dispatch() called before freeze(). "
                "Registration MUST complete and freeze() MUST be called before dispatch.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        if not topic or not topic.strip():
            raise ModelOnexError(
                message="Topic cannot be empty or whitespace.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        if envelope is None:
            raise ModelOnexError(
                message="Cannot dispatch None envelope. ModelEventEnvelope is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        dispatch_id = uuid4()
        started_at = datetime.now(UTC)
        correlation_id = self._extract_correlation_id(envelope)

        # Step 1: parse topic -> category. No category => INVALID_MESSAGE (no DLQ,
        # no message_category/type recorded), matching the engine's early return.
        topic_category = EnumMessageCategory.from_topic(topic)
        if topic_category is None:
            return ModelDispatchResult(
                dispatch_id=dispatch_id,
                status=EnumDispatchStatus.INVALID_MESSAGE,
                topic=topic,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                error_message=(
                    f"Cannot infer message category from topic '{topic}'. "
                    "Topic must contain .events, .commands, .intents, or .projections segment."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                correlation_id=correlation_id,
                output_events=[],
            )

        # Step 2: routing key from event_type (preferred) or payload class name.
        event_type, payload = self._extract_routing_inputs(envelope)
        normalized_event_type = (
            str(event_type).strip() if event_type is not None else ""
        )
        message_type = (
            normalized_event_type if normalized_event_type else type(payload).__name__
        )

        # Step 3: selection.
        matching = self._find_matching_dispatchers(
            topic=topic,
            category=topic_category,
            message_type=message_type,
            payload=payload,
        )

        if not matching:
            dlq_topic = self._derive_dlq_topic(
                normalized_event_type if normalized_event_type else None, topic
            )
            return ModelDispatchResult(
                dispatch_id=dispatch_id,
                status=EnumDispatchStatus.NO_DISPATCHER,
                topic=topic,
                message_category=topic_category,
                message_type=message_type,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                dlq_topic=dlq_topic,
                error_message=(
                    f"No dispatcher registered for category '{topic_category}' "
                    f"and message type '{message_type}' matching topic '{topic}'."
                ),
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                correlation_id=correlation_id,
                output_events=[],
            )

        ordered_ids = [entry.dispatcher_id for entry in matching]
        matched_route_id = self._first_matching_route_id(
            topic, topic_category, message_type
        )
        return ModelDispatchResult(
            dispatch_id=dispatch_id,
            status=EnumDispatchStatus.SUCCESS,
            route_id=matched_route_id,
            dispatcher_id=", ".join(ordered_ids),
            topic=topic,
            message_category=topic_category,
            message_type=message_type,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            output_count=0,
            output_events=[],
            correlation_id=correlation_id,
        )

    # -- helpers --------------------------------------------------------------

    def _derive_dlq_topic(self, event_type: str | None, topic: str) -> str | None:
        """Delegate to the injected deriver; ``None`` when none is configured."""
        deriver = self._state().dlq_topic_deriver
        if deriver is None:
            return None
        try:
            return deriver(event_type, topic)
        except Exception:  # noqa: BLE001 — DLQ derivation must never crash selection
            return None

    def _first_matching_route_id(
        self,
        topic: str,
        category: EnumMessageCategory,
        message_type: str,
    ) -> str | None:
        """First route (insertion order) fully matching topic/category/type, for
        logging parity with the engine's ``matched_route_id``."""
        for route in self._state().routes.values():
            if route.matches(topic, category, message_type):
                return route.route_id
        return None

    @staticmethod
    def _extract_routing_inputs(envelope: object) -> tuple[object | None, object]:
        """Extract ``(event_type, payload)`` from dict or model envelopes, matching
        the engine's field-presence handling.

        ``envelope`` is typed ``object`` (not ``ModelEventEnvelope``) because the
        runtime may hand this mixin a raw dict envelope on some paths; the dict
        branch would otherwise be statically unreachable.
        """
        if isinstance(envelope, dict):
            return envelope.get("event_type"), envelope.get("payload", envelope)
        return getattr(envelope, "event_type", None), getattr(envelope, "payload", None)

    @staticmethod
    def _extract_correlation_id(envelope: object) -> UUID:
        """Correlation id from the envelope, auto-generated when absent (parity
        with the engine's ``envelope.correlation_id or uuid4()``)."""
        if isinstance(envelope, dict):
            existing = envelope.get("correlation_id")
        else:
            existing = getattr(envelope, "correlation_id", None)
        if isinstance(existing, UUID):
            return existing
        return uuid4()
