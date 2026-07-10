# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Local runtime orchestrator for contract-declared workflows.

RuntimeLocal loads a workflow contract, discovers and wires nodes,
starts the in-memory event bus, publishes the initial command, and
waits for the terminal event declared in the contract.

Terminal states:
- COMPLETED — terminal event received, evidence written (exit 0)
- TIMEOUT — ``--timeout`` exceeded without terminal event (exit 1)
- PARTIAL — some evidence written but no terminal event (exit 3)
- FAILED — terminal event received with failure payload (exit 1)
"""

from __future__ import annotations

__all__ = ["RuntimeLocal"]

import asyncio
import importlib
import importlib.metadata
import inspect
import json
import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
    UnsubscribeCallback,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_dump_model import (
    ProtocolLocalRuntimeDumpModel,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_payload_model import (
    ProtocolLocalRuntimePayloadModel,
)

logger = logging.getLogger(__name__)

# Known backend protocol keys that --backend can override.
# kafka_bootstrap is a Kafka-specific tuning knob: when ``event_bus=kafka`` is
# selected, callers may pass ``--backend kafka_bootstrap=host:port`` to override
# the default bootstrap server (otherwise read from ``KAFKA_BOOTSTRAP_SERVERS``
# env var or the provider's config defaults).
KNOWN_BACKEND_KEYS: frozenset[str] = frozenset(
    {"event_bus", "state_store", "metrics", "tracing", "kafka_bootstrap"}
)

# Entry-point group that backend providers (e.g. omnibase_infra) register under.
# omnibase_core MUST NOT import omnibase_infra directly (compat→core→spi→infra
# layering is enforced by sdk-boundary-check CI). Instead, when the runtime
# needs a non-default bus implementation it discovers the class via this
# ``importlib.metadata`` group, which omnibase_infra populates in its
# ``[project.entry-points."onex.backends"]`` table.
_BACKEND_ENTRY_POINT_GROUP: str = "onex.backends"
_KAFKA_EVENT_BUS_ENTRY_POINT: str = "event_bus_kafka"

# Whitelist of accepted ``backend_overrides['event_bus']`` values. Anything
# outside this set is a typo (e.g. ``event_bus=kafak``) or a misconfigured
# stack and is rejected with ``CONFIGURATION_ERROR`` rather than silently
# downgrading to the in-memory bus. ``inmemory`` and the in-tree default
# (no override) both resolve to ``EventBusInmemory``; ``kafka`` resolves via
# the ``onex.backends`` entry-point group.
SUPPORTED_EVENT_BUS_VALUES: frozenset[str] = frozenset({"inmemory", "kafka"})

# Handler-result ``status`` values that unambiguously mean the run failed.
# Effect/reducer handlers report failures in-band by returning an error-shaped
# response envelope (``status="error"`` plus an ``error_message``) rather than
# raising — e.g. the "Handler not initialized" envelope every init/execute
# handler emits before ``initialize()`` has run. Before OMN-14298 the classifier
# recognised only ``status == "failure"``, so such runs were misclassified
# COMPLETED (exit 0) — a false green over a broken run.
_FAILURE_STATUS_VALUES: frozenset[str] = frozenset({"failure", "failed", "error"})

# Handler-result ``status`` values that unambiguously mean the run succeeded.
# ``no_results`` in particular is a successful query that simply matched nothing
# and must never be classified FAILED. An explicit success status short-circuits
# the error-attribute heuristic below.
_SUCCESS_STATUS_VALUES: frozenset[str] = frozenset(
    {
        "success",
        "ok",
        "completed",
        "complete",
        "no_results",
        "healthy",
        "passed",
        "pass",
    }
)

RawWorkflowMap = dict[str, object]
RuntimeCallable = Callable[..., object]


@dataclass(
    frozen=True
)  # internal-dataclass-ok: module-internal routing entry used only within runtime_local.py
class ResolvedRoutingEntry:
    """A single resolved handler routing entry with concrete topics."""

    handler_module: str
    handler_class: str
    handler_name: str
    event_model_module: str
    event_model_class: str
    input_topic: str
    output_topic: str


def _exit_code_for(result: EnumWorkflowResult) -> int:
    """Map a workflow result to the appropriate CLI exit code."""
    _map: dict[EnumWorkflowResult, int] = {
        EnumWorkflowResult.COMPLETED: EnumCLIExitCode.SUCCESS,
        EnumWorkflowResult.TIMEOUT: EnumCLIExitCode.ERROR,
        EnumWorkflowResult.PARTIAL: EnumCLIExitCode.PARTIAL,
        EnumWorkflowResult.FAILED: EnumCLIExitCode.ERROR,
    }
    return _map[result]


def parse_backend_overrides(raw: tuple[str, ...]) -> dict[str, str]:
    """Parse and validate ``--backend key=value`` flags.

    Args:
        raw: Tuple of ``"key=value"`` strings from Click's ``multiple`` option.

    Returns:
        Validated mapping of backend keys to backend names.

    Raises:
        ModelOnexError: If a key is unknown or the format is invalid.
    """
    overrides: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            msg = (
                f"Invalid --backend format '{item}'. "
                "Expected key=value (e.g. --backend event_bus=inmemory)."
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT, message=msg
            )
        key, value = item.split("=", 1)
        if key not in KNOWN_BACKEND_KEYS:
            sorted_keys = ", ".join(sorted(KNOWN_BACKEND_KEYS))
            msg = f"Unknown backend key '{key}'. Known keys: {sorted_keys}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT, message=msg
            )
        overrides[key] = value
    return overrides


# ONEX_EXCLUDE: dict_str_any — workflow contract has no fixed Pydantic model yet
def load_workflow_contract(
    path: Path,
) -> RawWorkflowMap:
    """Load and minimally validate a workflow contract YAML.

    Args:
        path: Filesystem path to the workflow contract.

    Returns:
        Parsed YAML as a dict.

    Raises:
        ModelOnexError: If *path* does not exist or the YAML is invalid.
    """
    if not path.exists():
        msg = f"Workflow contract not found: {path}"
        raise ModelOnexError(error_code=EnumCoreErrorCode.FILE_NOT_FOUND, message=msg)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Unable to read workflow contract: {path}"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            message=msg,
        ) from exc
    try:
        data = yaml.safe_load(
            text
        )  # yaml-safe-load-ok: loading contract for Pydantic validation downstream
    except yaml.YAMLError as exc:
        msg = f"Workflow contract is not valid YAML: {path}"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        ) from exc

    if not isinstance(data, dict):
        msg = f"Workflow contract must be a YAML mapping, got {type(data).__name__}"
        raise ModelOnexError(error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)

    return cast("RawWorkflowMap", data)


class RuntimeLocal:
    """Local runtime orchestrator.

    Executes a contract-declared workflow using in-memory backends by default.
    The workflow contract must declare a ``terminal_event`` topic; the runtime
    subscribes to that topic and treats the first message as the completion
    signal.

    Args:
        workflow_path: Path to the workflow contract YAML.
        state_root: Root directory for disk state (default ``.onex_state``).
        backend_overrides: Optional backend key-value overrides.
        timeout: Maximum execution time in seconds (default 300).
    """

    def __init__(
        self,
        workflow_path: Path,
        *,
        state_root: Path = Path(".onex_state"),
        backend_overrides: dict[str, str] | None = None,
        input_path: Path | None = None,
        timeout: int = 300,
    ) -> None:
        self.workflow_path = workflow_path
        self.state_root = state_root
        self.backend_overrides = backend_overrides or {}
        self.input_path = input_path
        self.timeout = timeout

        self._contract: RawWorkflowMap = {}
        self._result: EnumWorkflowResult = EnumWorkflowResult.TIMEOUT
        self._terminal_received = asyncio.Event()

        # Diagnostic tracking: events received per topic
        self._events_received: dict[str, int] = {}
        self._last_error: str | None = None
        self._handlers_wired: list[str] = []
        self._terminal_payload: RawWorkflowMap | None = None
        self._handler_result: object | None = None

    # ONEX_EXCLUDE: dict_str_any — event bus payload
    def _on_terminal_event(self, payload: RawWorkflowMap) -> None:
        """Callback invoked when a message arrives on the terminal_event topic."""
        self._record_event("(terminal)")
        if self._terminal_received.is_set():
            logger.warning("Duplicate terminal event received — ignoring (first wins).")
            return

        status = payload.get("status", "success")
        logger.info("RuntimeLocal: terminal event received (status=%s)", status)
        self._terminal_payload = payload
        self._result = self._classify_result(payload)

        self._terminal_received.set()

    # ------------------------------------------------------------------
    # Routing detection
    # ------------------------------------------------------------------

    def _has_event_routing(self) -> bool:
        """Return True if the contract declares event-driven handler routing."""
        routing = self._contract.get("handler_routing")
        return (
            isinstance(routing, dict)
            and isinstance(routing.get("handlers"), list)
            and len(routing["handlers"]) > 0
        )

    @staticmethod
    def _as_workflow_map(value: object) -> RawWorkflowMap:
        """Return ``value`` as a workflow map when the YAML shape is mapping-like."""
        return cast("RawWorkflowMap", value) if isinstance(value, dict) else {}

    @staticmethod
    def _as_workflow_maps(value: object) -> list[RawWorkflowMap]:
        """Return mapping items from a YAML list, dropping malformed entries."""
        if not isinstance(value, list):
            return []
        return [
            cast("RawWorkflowMap", item) for item in value if isinstance(item, dict)
        ]

    @staticmethod
    def _as_string_list(value: object) -> list[str]:
        """Return string values from a YAML list."""
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    # ------------------------------------------------------------------
    # Handler instantiation (shared helper)
    # ------------------------------------------------------------------

    def _instantiate_handler(
        self,
        module_name: str,
        class_name: str,
        *,
        bus: ProtocolLocalRuntimeBus | None = None,
    ) -> object:
        """Import *module_name*, resolve *class_name*, and return an instance.

        Runtime-owned dependencies are injected explicitly when the constructor
        advertises a supported parameter:

        * ``state_root`` — injected with the runtime's disk-state root.
        * ``event_bus`` — injected with the in-scope runtime *bus* when one is
          provided. Handlers that publish telemetry (e.g. the omnimarket sweep
          and orchestrator handlers) declare a mandatory ``event_bus`` positional
          arg; without this injection they fail to instantiate with
          ``__init__() missing 1 required positional argument: 'event_bus'``
          (OMN-13515). The bus is in scope at the event-driven and single-handler
          call sites; the compute path owns no bus and passes ``bus=None``.

        Args:
            module_name: Dotted module path containing the handler class.
            class_name: Handler class name within *module_name*.
            bus: The runtime event bus, threaded from the calling execution path.
                ``None`` on paths that own no bus (e.g. ``_run_compute``).

        Raises:
            ModelOnexError: If the module cannot be imported or the class is missing.
        """
        try:
            mod = importlib.import_module(module_name)
            handler_cls = getattr(mod, class_name)
        except (ImportError, AttributeError) as exc:
            msg = f"Failed to resolve handler {module_name}.{class_name}: {exc}"
            logger.exception("RuntimeLocal: %s", msg)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                message=msg,
            ) from exc

        kwargs: dict[str, object] = {}
        try:
            sig = inspect.signature(handler_cls.__init__)
            for param_name in sig.parameters:
                if param_name == "state_root":
                    kwargs[param_name] = self.state_root
                elif param_name == "event_bus" and bus is not None:
                    kwargs[param_name] = bus
        except (ValueError, TypeError):
            # If signature inspection fails, instantiate with no kwargs.
            pass

        instance = handler_cls(**kwargs)
        logger.info(
            "RuntimeLocal: instantiated handler %s.%s",
            module_name,
            class_name,
        )
        return instance

    # Fallback method names for handlers that lack handle().
    _FALLBACK_METHODS: tuple[str, ...] = ("run_full_cycle", "run", "execute")

    def _resolve_handler_method(
        self, handler_instance: object, class_name: str
    ) -> tuple[RuntimeCallable | None, str]:
        """Resolve the entry method on a handler instance.

        Prefers ``handle()``. If absent, tries ``run_full_cycle``, ``run``,
        ``execute`` in order. Returns ``(method, name)`` or ``(None, "")``
        if no callable entry point is found.
        """
        handle_method = getattr(handler_instance, "handle", None)
        if callable(handle_method):
            return cast("RuntimeCallable", handle_method), "handle"

        for name in self._FALLBACK_METHODS:
            method = getattr(handler_instance, name, None)
            if callable(method):
                logger.info(
                    "RuntimeLocal: handler %s has no handle() — falling back to %s()",
                    class_name,
                    name,
                )
                return cast("RuntimeCallable", method), name

        logger.error(
            "Handler %s has no handle(), run_full_cycle(), run(), or execute() method",
            class_name,
        )
        return None, ""

    @staticmethod
    def _handler_reports_initialized(handler_instance: object) -> bool:
        """Return True if the handler already reports itself initialized.

        Honors a public ``is_initialized`` property first, then the private
        ``_initialized`` flag the ONEX init/execute handlers set. Anything else
        (attribute absent, non-bool) is treated as "not initialized" so the
        guard errs toward calling ``initialize()``.
        """
        is_init = getattr(handler_instance, "is_initialized", None)
        if isinstance(is_init, bool):
            return is_init
        return getattr(handler_instance, "_initialized", None) is True

    async def _ensure_handler_initialized(self, handler_instance: object) -> None:
        """Call ``handler.initialize()`` before invoking its entry method (OMN-14298).

        ONEX effect/reducer handlers use an ``initialize()`` / ``execute()``
        lifecycle: ``execute()`` returns a "Handler not initialized" error
        envelope until ``initialize()`` has run. RuntimeLocal previously invoked
        the fallback ``execute()`` (or ``run()``) method WITHOUT ``initialize()``,
        so every such node returned a not-initialized error that the runtime then
        misclassified as COMPLETED — the systemic false-green this fix closes.

        The call is guarded and idempotent:
        - no-op when the handler declares no callable ``initialize``
        - no-op when the handler already reports itself initialized
          (``is_initialized`` / ``_initialized``); the handlers also guard
          internally, so a redundant call is harmless
        - no-op (with a warning) when ``initialize()`` declares required
          parameters the runtime cannot supply (e.g. a graph ``connection_uri``);
          ``execute()`` then surfaces the real not-initialized state, which
          ``_classify_result`` maps to FAILED rather than a false COMPLETED.

        Any exception raised *inside* a zero-argument ``initialize()`` propagates
        so the run is recorded FAILED (via ``run_async``'s handler) rather than
        silently green.
        """
        initialize = getattr(handler_instance, "initialize", None)
        if not callable(initialize):
            return
        if self._handler_reports_initialized(handler_instance):
            return

        try:
            sig = inspect.signature(initialize)
        except (TypeError, ValueError):
            sig = None
        if sig is not None:
            required = [
                param.name
                for param in sig.parameters.values()
                if param.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
                and param.default is inspect.Parameter.empty
            ]
            if required:
                logger.warning(
                    "RuntimeLocal: %s.initialize() requires parameter(s) %s the "
                    "runtime cannot supply — skipping initialize(); execute() will "
                    "report its real lifecycle state",
                    type(handler_instance).__name__,
                    required,
                )
                return

        logger.info(
            "RuntimeLocal: calling %s.initialize() before invocation",
            type(handler_instance).__name__,
        )
        await self._maybe_await(initialize())

    async def _invoke_handler_method(
        self,
        method: RuntimeCallable,
        method_name: str,
        handler_instance: object,
        initial_payload: object,
    ) -> object:
        """Invoke a handler method, adapting the call signature as needed.

        ``handle()`` receives a single positional payload argument.
        ``run_full_cycle()`` receives a typed command model as its first arg.
        ``run()`` and ``execute()`` are tried with payload first, then without.

        Handlers exposing an ``initialize()`` lifecycle are initialized first via
        ``_ensure_handler_initialized`` (OMN-14298) so ``execute()`` does not
        return a spurious "Handler not initialized" error.
        """
        await self._ensure_handler_initialized(handler_instance)
        try:
            result = await self._maybe_await(method(initial_payload))
        except TypeError as original_exc:
            # The method may not accept arguments (e.g. run() with no args).
            # Retry without args; if that also fails, re-raise the original.
            try:  # fallback-ok: adapt no-argument handler methods while preserving the original TypeError
                result = await self._maybe_await(method())
            except TypeError:
                raise original_exc from None

        # run_full_cycle returns (state, events, completed_event) — extract
        # the completed event for result classification.
        if isinstance(result, tuple) and len(result) >= 3:
            result = result[-1]

        return result

    @staticmethod
    async def _maybe_await(value: object) -> object:
        """Await decorated async call results that are not coroutine functions."""
        if inspect.isawaitable(value):
            awaitable_value: Awaitable[object] = cast("Awaitable[object]", value)
            return await awaitable_value
        return value

    @staticmethod
    def _correlation_id_from_payload(payload: object) -> str | None:
        """Extract an existing correlation ID from a typed or mapping payload."""
        if isinstance(payload, dict):
            value = payload.get("correlation_id")
        else:
            value = getattr(payload, "correlation_id", None)
        if value:
            return str(value)
        return None

    # ------------------------------------------------------------------
    # Single-handler execution path
    # ------------------------------------------------------------------

    async def _run_single_handler(
        self, bus: ProtocolLocalRuntimeBus, terminal_topic: str
    ) -> None:
        """Resolve and invoke the single handler declared in the contract.

        If the handler returns a result directly, it is classified immediately.
        Otherwise (e.g. handler publishes to the bus and the terminal event
        arrives asynchronously), the method waits up to ``self.timeout`` seconds
        for the terminal event.

        The terminal topic subscription is owned by this method (not
        ``run_async``) so that event-driven workflows—which subscribe to
        terminal topics via ``publish_topics``—don't receive duplicates.
        """

        async def _on_terminal_msg(msg: ProtocolLocalRuntimeMessage) -> None:
            """Adapt async bus callback to sync terminal handler."""
            decoded: object = (
                json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            )
            payload = decoded if isinstance(decoded, dict) else {}
            self._on_terminal_event(cast("RawWorkflowMap", payload))

        await bus.subscribe(
            terminal_topic,
            on_message=_on_terminal_msg,
            group_id="runtime-local-terminal",
        )
        logger.info("RuntimeLocal: subscribed to terminal topic '%s'", terminal_topic)

        handler_spec = self._as_workflow_map(self._contract.get("handler", {}))
        handler_module_name = handler_spec.get("module", "")
        handler_class_name = handler_spec.get("class", "")

        # Fallback: resolve from handler_routing.default_handler
        if not handler_module_name or not handler_class_name:
            resolved = self._resolve_default_handler()
            if resolved is not None:
                handler_module_name, handler_class_name = resolved
            else:
                logger.error(
                    "Workflow contract missing handler.module or handler.class "
                    "and no valid handler_routing.default_handler found"
                )
                self._result = EnumWorkflowResult.FAILED
                return

        handler_module = str(handler_module_name)
        handler_class = str(handler_class_name)
        self._handlers_wired = [f"{handler_module}.{handler_class}"]

        handler_instance = self._instantiate_handler(
            handler_module, handler_class, bus=bus
        )

        # Build initial payload from handler or contract input spec.
        # input_model may be a dotted string ("module.ClassName") — coerce to dict.
        input_spec_raw: object = handler_spec.get(
            "input_model", {}
        ) or self._contract.get("input", {})
        input_spec: object
        if isinstance(input_spec_raw, dict):
            input_spec = cast("RawWorkflowMap", input_spec_raw)
        elif isinstance(input_spec_raw, str):
            input_spec = input_spec_raw
        else:
            input_spec = {}
        if isinstance(input_spec, str) and "." in input_spec:
            module_name, class_name = input_spec.rsplit(".", 1)
            input_spec = {"module": module_name, "class": class_name}
        elif not isinstance(input_spec, dict):
            input_spec = {}
        initial_payload = self._build_initial_payload(
            cast("RawWorkflowMap", input_spec)
        )

        # Invoke handler — prefer handle(), fall back to run_full_cycle/run/execute
        handle_method, method_name = self._resolve_handler_method(
            handler_instance, handler_class
        )
        if handle_method is None:
            self._result = EnumWorkflowResult.FAILED
            return

        result_obj = await self._invoke_handler_method(
            handle_method, method_name, handler_instance, initial_payload
        )
        correlation_id = self._correlation_id_from_payload(initial_payload)

        # If the handler returned a result, use it directly — don't wait for
        # terminal event since single-handler workflows return synchronously.
        # If terminal_received is already set (e.g. by _on_terminal_event with a
        # failure), preserve that result rather than overwriting with a classification
        # of None.
        if result_obj is not None:
            self._handler_result = result_obj
            self._result = self._classify_result(result_obj)
            await self._publish_synthesized_terminal(
                bus, terminal_topic, correlation_id=correlation_id
            )
            logger.info("RuntimeLocal: handler returned, result=%s", self._result.value)
            return

        if self._terminal_received.is_set():
            logger.info("RuntimeLocal: handler returned, result=%s", self._result.value)
            return

        # Handler returned success-ish but terminal event may still arrive async.
        if not self._terminal_received.is_set():
            try:
                await asyncio.wait_for(
                    self._terminal_received.wait(), timeout=self.timeout
                )
            except TimeoutError:
                timeout_correlation_id = str(
                    self._contract.get("correlation_id", "unknown")
                )
                logger.warning(
                    "RuntimeLocal: timeout (%ds) waiting for terminal event "
                    "[correlation_id=%s]",
                    self.timeout,
                    timeout_correlation_id,
                )
                self._result = EnumWorkflowResult.TIMEOUT
                self._log_timeout_summary()
                return

        logger.info("RuntimeLocal: handler returned, result=%s", self._result.value)

    async def _publish_synthesized_terminal(
        self,
        bus: ProtocolLocalRuntimeBus,
        terminal_topic: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a runtime-synthesized terminal event after sync-return classification.

        Runtime behavior decision (OMN-8940): synchronous-return handlers in the
        single-handler execution path bypass the bus today — ``_run_single_handler``
        classifies the handler's return value directly and sets ``self._result`` without
        publishing to the terminal topic. This method adopts the rule that
        ``RuntimeLocal`` publishes a terminal event after successful classification so
        the bus participates in every completed workflow regardless of handler return
        style.

        Payload shape::

            {"status": "success" | "failure",
             "correlation_id": "<uuid>",
             "source": "runtime_local"}

        The ``source`` field lets downstream consumers distinguish runtime-synthesized
        from handler-published terminals. Fires for both COMPLETED and FAILED paths;
        silence on failure would be worse than a documented failure event.

        This helper is called *only* by ``_run_single_handler``. The event-driven path
        (``_run_event_driven``) already relies on handler-published terminals and must
        not double-emit.
        """
        status_payload = (
            "success" if self._result == EnumWorkflowResult.COMPLETED else "failure"
        )
        await bus.publish(
            terminal_topic,
            None,
            json.dumps(
                {
                    "status": status_payload,
                    "correlation_id": correlation_id or str(uuid.uuid4()),
                    "source": "runtime_local",
                }
            ).encode("utf-8"),
        )

    # ------------------------------------------------------------------
    # Event-driven execution path
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_handler_input_topic(
        entry: RawWorkflowMap,
        idx: int,
        subscribe_topics: list[str],
    ) -> str | None:
        """Resolve the input topic for a single handler entry.

        Prefers an explicit ``subscribe_topic`` field on the handler entry.
        Falls back to positional lookup (``subscribe_topics[idx]``) for
        backward-compatible contracts that omit the field.

        Returns the resolved topic string, or ``None`` if neither source
        provides a valid topic (e.g. terminal reducer with no positional slot).
        """
        if "subscribe_topic" in entry:
            explicit = entry["subscribe_topic"]
            if explicit is None:
                return None
            return str(explicit)
        if idx < len(subscribe_topics):
            return subscribe_topics[idx]
        return None

    @staticmethod
    def _validate_routing(
        routing: RawWorkflowMap,
        subscribe_topics: list[str],
        publish_topics: list[str],
    ) -> list[str]:
        """Validate handler routing entries against topic lists.

        Uses a map-based check: every handler must resolve an input topic that
        exists in ``subscribe_topics`` (via explicit ``subscribe_topic`` field
        or positional fallback). Terminal reducers with no ``publish_topic`` /
        ``output_events`` are valid — they do not require padding.

        Returns:
            List of validation error messages (empty means valid).
        """
        handlers = RuntimeLocal._as_workflow_maps(routing.get("handlers", []))
        errors: list[str] = []
        input_topic_set = set(subscribe_topics)
        strategy = str(routing.get("routing_strategy", ""))

        # Per-entry field and topic validation
        for i, entry in enumerate(handlers):
            prefix = f"handlers[{i}]"
            em = RuntimeLocal._as_workflow_map(entry.get("event_model", {}))
            hd = RuntimeLocal._as_workflow_map(entry.get("handler", {}))
            if strategy == "payload_type_match":
                # payload_type_match routes by model type — event_model is required.
                if not em.get("name"):
                    errors.append(f"{prefix}.event_model.name is missing")
                if not em.get("module"):
                    errors.append(f"{prefix}.event_model.module is missing")
            else:
                # operation_match (and any future non-payload strategies) route by
                # the `operation` field — event_model is not used and must not be
                # required here. Require `operation` instead.
                op = entry.get("operation")
                if not op:
                    errors.append(f"{prefix}.operation is missing")
            if not hd.get("name"):
                errors.append(f"{prefix}.handler.name is missing")
            if not hd.get("module"):
                errors.append(f"{prefix}.handler.module is missing")

            # Resolve input topic; terminal reducers with no positional slot are
            # valid (no error) — they simply receive no events via the bus.
            resolved_topic = RuntimeLocal._resolve_handler_input_topic(
                entry, i, subscribe_topics
            )
            if resolved_topic is not None and resolved_topic not in input_topic_set:
                errors.append(
                    f"{prefix}.subscribe_topic '{resolved_topic}' is not in "
                    f"event_bus.subscribe_topics"
                )

        # Collect all event_model.name values and publish_topics for output
        # validation
        known_event_names = {
            RuntimeLocal._as_workflow_map(e.get("event_model", {})).get("name")
            for e in handlers
            if RuntimeLocal._as_workflow_map(e.get("event_model", {})).get("name")
        }
        for i, entry in enumerate(handlers):
            prefix = f"handlers[{i}]"
            output_events = RuntimeLocal._as_string_list(entry.get("output_events", []))
            for out_evt in output_events:
                if out_evt not in known_event_names and not publish_topics:
                    errors.append(
                        f"{prefix}.output_events entry '{out_evt}' does not "
                        f"match any downstream handler event_model.name and "
                        f"no publish_topics defined for terminal output"
                    )

        return errors

    def _resolve_routing_entries(
        self,
        routing: RawWorkflowMap,
        subscribe_topics: list[str],
        publish_topics: list[str],
    ) -> list[ResolvedRoutingEntry]:
        """Build resolved routing entries with concrete input/output topics."""
        handlers = self._as_workflow_maps(routing.get("handlers", []))

        # Build index: event_model.name -> subscribe_topics index
        name_to_topic_idx: dict[str, int] = {}
        for i, entry in enumerate(handlers):
            event_model = self._as_workflow_map(entry.get("event_model", {}))
            em_name = event_model.get("name", "")
            if isinstance(em_name, str) and em_name:
                name_to_topic_idx[em_name] = i

        resolved: list[ResolvedRoutingEntry] = []
        for i, entry in enumerate(handlers):
            em = self._as_workflow_map(entry.get("event_model", {}))
            hd = self._as_workflow_map(entry.get("handler", {}))
            output_events = self._as_string_list(entry.get("output_events", []))
            input_topic = (
                self._resolve_handler_input_topic(entry, i, subscribe_topics) or ""
            )

            # Determine output topic
            output_topic = ""
            if output_events:
                first_output = output_events[0]
                downstream_idx = name_to_topic_idx.get(first_output)
                if downstream_idx is not None:
                    downstream_entry = handlers[downstream_idx]
                    downstream_topic = self._resolve_handler_input_topic(
                        downstream_entry, downstream_idx, subscribe_topics
                    )
                    output_topic = downstream_topic or ""
                elif publish_topics:
                    output_topic = publish_topics[0]
            elif input_topic and publish_topics:
                terminal_topic = self._contract.get("terminal_event")
                output_topic = (
                    terminal_topic
                    if isinstance(terminal_topic, str)
                    and terminal_topic in publish_topics
                    else publish_topics[0]
                )

            resolved.append(
                ResolvedRoutingEntry(
                    handler_module=str(hd.get("module", "")),
                    handler_class=str(hd.get("name", "")),
                    handler_name=str(hd.get("name", "unknown")),
                    event_model_module=str(em.get("module", "")),
                    event_model_class=str(em.get("name", "")),
                    input_topic=input_topic,
                    output_topic=output_topic,
                )
            )

        return resolved

    @staticmethod
    def _coerce_model_spec(raw: object) -> RawWorkflowMap | None:
        """Coerce a contract model reference to a ``{module, class}`` spec.

        Accepts either a dotted string ``"some.module.ClassName"`` or a mapping.
        Mappings may use ``class`` or ``name`` for the class key (the routing
        ``event_model`` block uses ``name``; the top-level ``input_model`` block
        uses ``class``). Returns ``None`` when no module/class can be resolved.
        """
        if isinstance(raw, str) and "." in raw:
            module_name, class_name = raw.rsplit(".", 1)
            if module_name and class_name:
                return {"module": module_name, "class": class_name}
            return None
        if isinstance(raw, dict):
            module = raw.get("module", "")
            cls = raw.get("class", "") or raw.get("name", "")
            if isinstance(module, str) and isinstance(cls, str) and module and cls:
                return {"module": module, "class": cls}
        return None

    def _resolve_event_driven_payload_spec(
        self, routing: RawWorkflowMap
    ) -> tuple[RawWorkflowMap, str] | None:
        """Resolve the initial-payload model spec for the event-driven path.

        Resolution order (mirrors ``_run_single_handler``, but for the routed
        path): top-level ``input_model`` → first handler routing entry's
        ``event_model`` → that entry's ``handler.input_model``. Returns the
        ``{module, class}`` spec and a human-readable source label describing
        where it was resolved from, or ``None`` when no model can be resolved.
        """
        top_spec = self._coerce_model_spec(self._contract.get("input_model", {}))
        if top_spec is not None:
            return top_spec, "contract.input_model"

        handlers = self._as_workflow_maps(routing.get("handlers", []))
        for entry in handlers:
            event_model = self._as_workflow_map(entry.get("event_model", {}))
            em_spec = self._coerce_model_spec(event_model)
            if em_spec is not None:
                em_name = event_model.get("name", "")
                return em_spec, f"handler_routing event_model '{em_name}'"

            handler_block = self._as_workflow_map(entry.get("handler", {}))
            hi_spec = self._coerce_model_spec(handler_block.get("input_model", {}))
            if hi_spec is not None:
                handler_name = handler_block.get("name", "unknown")
                return hi_spec, f"handler_routing handler '{handler_name}'.input_model"

        # Final fallback: an operation_match handler declares no event_model and
        # no handler.input_model, but its ``handle`` method takes a single
        # positional parameter annotated with a concrete BaseModel subclass (the
        # OMN-8724 typed-parameter shape, e.g.
        # ``handle(self, request: GoldenChainSweepRequest)``). The adapter would
        # coerce the seeded dict into that model at the call boundary, so the
        # model IS handler-derivable — seed the full payload from the annotation
        # rather than failing loud or degrading to {correlation_id}.
        for entry in handlers:
            handler_block = self._as_workflow_map(entry.get("handler", {}))
            module = handler_block.get("module", "")
            cls = handler_block.get("name", "")
            if not (
                isinstance(module, str) and isinstance(cls, str) and module and cls
            ):
                continue
            param_spec = self._handler_param_model_spec(module, cls)
            if param_spec is not None:
                return param_spec, f"handler '{cls}'.handle parameter annotation"

        return None

    @staticmethod
    def _handler_param_model_spec(
        handler_module: str, handler_class: str
    ) -> RawWorkflowMap | None:
        """Resolve a handler's sole typed-model ``handle`` parameter to a spec.

        Imports ``handler_module.handler_class`` and inspects its ``handle``
        method. When that method has exactly one positional parameter annotated
        with a concrete ``BaseModel`` subclass, returns the ``{module, class}``
        of that annotation. Returns ``None`` on any failure (import error, no
        ``handle``, untyped/multi-parameter signature) — the caller then fails
        loud. ``eval_str=True`` resolves PEP 563 string annotations (every node
        handler uses ``from __future__ import annotations``).
        """
        try:
            mod = importlib.import_module(handler_module)
            handler_cls = getattr(mod, handler_class)
            handle_method = handler_cls.handle
        except (ImportError, AttributeError):
            return None

        try:
            signature = inspect.signature(handle_method, eval_str=True)
        except (TypeError, ValueError, NameError):
            return None

        positional = [
            param
            for name, param in signature.parameters.items()
            if name != "self"
            and param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and param.default is inspect.Parameter.empty
        ]
        if len(positional) != 1:
            return None
        annotation = positional[0].annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return {"module": annotation.__module__, "class": annotation.__name__}
        return None

    async def _run_event_driven(self, bus: ProtocolLocalRuntimeBus) -> None:
        """Execute the workflow using event-driven handler routing.

        Reads handler_routing.handlers from the contract, validates the
        routing graph, wires LocalRuntimeBusAdapters to the in-memory event bus,
        publishes the initial command, and awaits the terminal event.
        """
        from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
            ProtocolLocalRuntimeCallableTarget,
        )
        from omnibase_core.runtime.runtime_local_adapter import (
            LocalRuntimeBusAdapter,
        )

        routing = self._as_workflow_map(self._contract.get("handler_routing", {}))
        event_bus_spec = self._as_workflow_map(self._contract.get("event_bus", {}))
        subscribe_topics = self._as_string_list(
            event_bus_spec.get("subscribe_topics", [])
        )
        publish_topics = self._as_string_list(event_bus_spec.get("publish_topics", []))
        terminal_topic = self._contract.get("terminal_event")
        if not isinstance(terminal_topic, str) or not terminal_topic:
            logger.error("RuntimeLocal: event-driven workflow missing terminal_event")
            self._result = EnumWorkflowResult.FAILED
            return
        if not subscribe_topics:
            logger.error(
                "RuntimeLocal: event-driven mode requires non-empty "
                "event_bus.subscribe_topics"
            )
            self._result = EnumWorkflowResult.FAILED
            return

        # --- 1. Validate routing (fail fast) ---
        validation_errors = self._validate_routing(
            routing, subscribe_topics, publish_topics
        )
        if validation_errors:
            for err in validation_errors:
                logger.error("RuntimeLocal: routing validation error: %s", err)
            self._result = EnumWorkflowResult.FAILED
            return

        # --- 2. Resolve routing entries ---
        resolved_entries = self._resolve_routing_entries(
            routing, subscribe_topics, publish_topics
        )

        # --- 3. Log the routing graph ---
        logger.info("RuntimeLocal: routing graph:")
        for entry in resolved_entries:
            logger.info(
                "  [%s] -> %s -> [%s]",
                entry.input_topic,
                entry.handler_name,
                entry.output_topic,
            )

        # --- 4. Wire adapters to bus ---
        unsubscribe_handles: list[UnsubscribeCallback] = []
        self._handlers_wired = [e.handler_name for e in resolved_entries]

        def _fail_callback() -> None:
            self._result = EnumWorkflowResult.FAILED
            self._terminal_received.set()

        for entry in resolved_entries:
            handler_instance = self._instantiate_handler(
                entry.handler_module, entry.handler_class, bus=bus
            )

            # Resolve the input model class. operation_match entries route by the
            # `operation` field and declare no event_model, so event_model_module is
            # empty — skip the import and forward the raw payload (OMN-13141). Only
            # payload_type_match entries carry a typed event model to import.
            input_model_type: type[BaseModel] | None = None
            if entry.event_model_module:
                try:
                    em_mod = importlib.import_module(entry.event_model_module)
                    input_model_type = cast(
                        "type[BaseModel]",
                        getattr(em_mod, entry.event_model_class),
                    )
                except (ImportError, AttributeError) as exc:
                    msg = (
                        f"Failed to resolve event model "
                        f"{entry.event_model_module}.{entry.event_model_class}: {exc}"
                    )
                    logger.exception("RuntimeLocal: %s", msg)
                    self._result = EnumWorkflowResult.FAILED
                    return

            def _make_fail_cb(name: str) -> Callable[[], None]:
                def _cb() -> None:
                    self._last_error = f"handler '{name}' failed"
                    _fail_callback()

                return _cb

            def _make_result_cb(output_topic: str) -> Callable[[object], None] | None:
                if output_topic != terminal_topic:
                    return None

                def _cb(result: object) -> None:
                    self._handler_result = result

                return _cb

            adapter = LocalRuntimeBusAdapter(
                handler=cast("ProtocolLocalRuntimeCallableTarget", handler_instance),
                handler_name=entry.handler_name,
                input_model_cls=input_model_type,
                output_topic=entry.output_topic or None,
                bus=bus,
                on_error=_make_fail_cb(entry.handler_name),
                on_result=_make_result_cb(entry.output_topic),
            )

            if not entry.input_topic:
                # Terminal reducer: no input topic, no bus subscription needed.
                logger.info(
                    "RuntimeLocal: handler '%s' has no input_topic — "
                    "skipping bus subscription (terminal reducer)",
                    entry.handler_name,
                )
                continue

            unsub = await bus.subscribe(
                entry.input_topic,
                on_message=adapter.on_message,
                group_id=f"runtime-local-{entry.handler_name}",
            )
            unsubscribe_handles.append(unsub)

        # --- 5. Subscribe to the declared terminal event only ---
        async def _on_terminal_msg(msg: ProtocolLocalRuntimeMessage) -> None:
            decoded: object = (
                json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            )
            payload = decoded if isinstance(decoded, dict) else {}
            self._on_terminal_event(cast("RawWorkflowMap", payload))

        unsub = await bus.subscribe(
            terminal_topic,
            on_message=_on_terminal_msg,
            group_id="runtime-local-terminal",
        )
        unsubscribe_handles.append(unsub)

        # --- 6. Build and publish initial payload ---
        correlation_id = uuid.uuid4()

        # Resolve the initial-payload model from, in order: top-level
        # ``input_model`` → first routing entry's ``event_model`` → that entry's
        # ``handler.input_model`` (OMN-13277). Previously this path consulted
        # only the top-level ``input_model`` and, when absent, published a
        # degenerate ``{correlation_id}``-only payload — silently dropping caller
        # input and masking the real validation error downstream (root cause of
        # OMN-13253). If NEITHER a top-level input_model NOR an event_model /
        # handler-derivable model can be resolved, fail loud here naming the
        # contract rather than publishing a degenerate payload.
        resolved_spec = self._resolve_event_driven_payload_spec(routing)
        if resolved_spec is None:
            contract_name = self._contract.get("name", "<unknown>")
            handler_names = [e.handler_name for e in resolved_entries] or ["<none>"]
            msg = (
                "RuntimeLocal: event-driven workflow could not resolve an "
                "initial-payload model for contract "
                f"'{contract_name}'. Declare a top-level 'input_model' (dotted "
                "path or {module, class}) or an 'event_model' / "
                "'handler.input_model' block on a handler_routing entry. "
                f"Handlers wired: {handler_names}. Refusing to publish a "
                "degenerate {correlation_id}-only payload that would silently "
                "drop caller input."
            )
            logger.error(msg)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                message=msg,
            )

        payload_spec, payload_source = resolved_spec
        logger.info(
            "RuntimeLocal: resolved initial-payload model %s.%s from %s",
            payload_spec["module"],
            payload_spec["class"],
            payload_source,
        )
        initial_payload = self._build_initial_payload(payload_spec)
        if initial_payload is None:
            contract_name = self._contract.get("name", "<unknown>")
            msg = (
                "RuntimeLocal: event-driven workflow resolved payload model "
                f"{payload_spec['module']}.{payload_spec['class']} (from "
                f"{payload_source}) for contract '{contract_name}' but failed to "
                "import/instantiate it. Refusing to publish a degenerate "
                "{correlation_id}-only payload that would silently drop caller "
                "input."
            )
            logger.error(msg)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                message=msg,
            )

        # Inject correlation_id if the model supports it
        if hasattr(initial_payload, "correlation_id"):
            try:
                payload_with_correlation: ProtocolLocalRuntimePayloadModel = cast(
                    "ProtocolLocalRuntimePayloadModel", initial_payload
                )
                payload_with_correlation.correlation_id = correlation_id
            except (AttributeError, ValueError):
                pass  # frozen model or incompatible type

        model_payload: ProtocolLocalRuntimePayloadModel = cast(
            "ProtocolLocalRuntimePayloadModel", initial_payload
        )
        await bus.publish(
            subscribe_topics[0],
            None,
            model_payload.model_dump_json().encode("utf-8"),
        )

        logger.info(
            "RuntimeLocal: published initial command to '%s' (correlation_id=%s)",
            subscribe_topics[0],
            correlation_id,
        )

        # --- 7. Await terminal with timeout ---
        try:
            await asyncio.wait_for(self._terminal_received.wait(), timeout=self.timeout)
        except TimeoutError:
            logger.warning(
                "RuntimeLocal: timeout after %ds (correlation_id=%s)",
                self.timeout,
                correlation_id,
            )
            self._result = EnumWorkflowResult.TIMEOUT
            self._log_timeout_summary()
        finally:
            for unsub in unsubscribe_handles:
                await unsub()

    # ------------------------------------------------------------------
    # Diagnostic helpers
    # ------------------------------------------------------------------

    def _record_event(self, topic: str) -> None:
        """Increment the event counter for *topic*."""
        self._events_received[topic] = self._events_received.get(topic, 0) + 1

    def _log_timeout_summary(self) -> None:
        """Log a diagnostic summary when the workflow times out."""
        logger.warning("--- timeout diagnostic summary ---")
        logger.warning("  handlers wired: %s", self._handlers_wired or "(none)")
        if self._events_received:
            for topic, count in self._events_received.items():
                logger.warning("  events on '%s': %d", topic, count)
        else:
            logger.warning("  events received: 0 (no messages on any topic)")
        if self._last_error:
            logger.warning("  last error: %s", self._last_error)
        logger.warning("--- end diagnostic summary ---")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Compute-node execution path (no terminal_event / event bus)
    # ------------------------------------------------------------------

    def _resolve_default_handler(self) -> tuple[str, str] | None:
        """Extract (module, class) from handler_routing.default_handler.

        The ``default_handler`` field uses ``module_ref:ClassName`` format.
        When ``module_ref`` is a bare name like ``handler``, it is resolved
        relative to the contract file's parent package (e.g.
        ``omnimarket.nodes.node_foo.handler`` for a contract at
        ``.../node_foo/contract.yaml``).

        Returns:
            ``(module_name, class_name)`` or ``None`` if not resolvable.
        """
        routing = self._contract.get("handler_routing")
        if not isinstance(routing, dict):
            return None
        default_handler = routing.get("default_handler")
        if not default_handler or not isinstance(default_handler, str):
            return None
        if ":" not in default_handler:
            return None

        module_ref, class_name = default_handler.rsplit(":", 1)

        # If module_ref looks like a bare name (no dots), try to resolve it
        # relative to the contract file's parent directory using the Python
        # package structure.
        if "." not in module_ref:
            contract_dir = self.workflow_path.resolve().parent
            resolved = self._infer_package_module(contract_dir, module_ref)
            if resolved == module_ref:
                # Could not resolve to a package-qualified path — accept as-is
                # only if the module is already importable (e.g. injected into
                # sys.modules at runtime).
                import sys as _sys

                if module_ref not in _sys.modules:
                    try:
                        __import__(module_ref)
                    except ImportError:
                        return None
            else:
                module_ref = resolved

        return (module_ref, class_name)

    @staticmethod
    def _infer_package_module(contract_dir: Path, relative_name: str) -> str:
        """Infer a fully-qualified module path from a contract directory.

        Walks up from *contract_dir* to find the nearest ancestor that is NOT
        a Python package (no ``__init__.py``), then builds the dotted path.

        Args:
            contract_dir: Directory containing ``contract.yaml``.
            relative_name: Bare module name (e.g. ``handler``).

        Returns:
            Dotted module path (e.g. ``omnimarket.nodes.node_foo.handler``).
            Falls back to *relative_name* if the package root can't be found.
        """
        parts: list[str] = [relative_name]
        current = contract_dir
        while (current / "__init__.py").exists():
            parts.insert(0, current.name)
            current = current.parent
        # Also check for src/ layout: if we stopped at a "src" directory,
        # skip it (it's not part of the package name).
        if parts and current.name == "src":
            pass  # parts are already correct
        return ".".join(parts) if len(parts) > 1 else relative_name

    def _resolve_handler_spec(self) -> tuple[str, str] | None:
        """Resolve handler (module, class) from available contract fields.

        Checks in order:
        1. ``handler_routing.default_handler`` (module:Class format)
        2. Top-level ``handler.module`` + ``handler.class``

        Returns:
            ``(module_name, class_name)`` or ``None``.
        """
        resolved = self._resolve_default_handler()
        if resolved is not None:
            return resolved

        handler_spec = self._contract.get("handler", {})
        if isinstance(handler_spec, dict):
            module_name = handler_spec.get("module", "")
            class_name = handler_spec.get("class", "")
            if module_name and class_name:
                return (module_name, class_name)

        return None

    async def _run_compute(self) -> None:
        """Execute a compute node's handler directly.

        No event bus or terminal_event is needed. The handler is resolved
        from ``handler_routing.default_handler`` or the top-level ``handler``
        spec, instantiated, and invoked. The return value determines the
        workflow result.
        """
        resolved = self._resolve_handler_spec()
        if resolved is None:
            logger.error(
                "RuntimeLocal: compute mode requires "
                "handler_routing.default_handler or handler.module/class"
            )
            self._result = EnumWorkflowResult.FAILED
            return

        module_name, class_name = resolved
        self._handlers_wired = [f"{module_name}.{class_name}"]

        handler_instance = self._instantiate_handler(module_name, class_name)

        handle_method, method_name = self._resolve_handler_method(
            handler_instance, class_name
        )
        if handle_method is None:
            self._result = EnumWorkflowResult.FAILED
            return

        # Build initial payload from handler or contract input spec
        handler_spec = self._as_workflow_map(self._contract.get("handler", {}))
        raw_contract_input: object = handler_spec.get(
            "input_model", {}
        ) or self._contract.get("input", {})
        input_spec_raw: object
        if isinstance(raw_contract_input, dict):
            input_spec_raw = cast("RawWorkflowMap", raw_contract_input)
        elif isinstance(raw_contract_input, str):
            input_spec_raw = raw_contract_input
        else:
            input_spec_raw = {}
        if isinstance(input_spec_raw, str) and "." in input_spec_raw:
            if not all(seg.isidentifier() for seg in input_spec_raw.split(".")):
                logger.warning(
                    "RuntimeLocal: invalid input_model format: %s",
                    input_spec_raw,
                )
                input_spec: RawWorkflowMap = {}
            else:
                im_module, im_class = input_spec_raw.rsplit(".", 1)
                input_spec = {"module": im_module, "class": im_class}
        elif isinstance(input_spec_raw, dict):
            input_spec = input_spec_raw
        else:
            input_spec = {}
        initial_payload = self._build_initial_payload(input_spec)

        logger.info(
            "RuntimeLocal: invoking compute handler %s.%s (method=%s)",
            module_name,
            class_name,
            method_name,
        )

        result_obj = await self._invoke_handler_method(
            handle_method, method_name, handler_instance, initial_payload
        )

        if result_obj is not None:
            self._handler_result = result_obj
        self._result = self._classify_result(result_obj)
        logger.info(
            "RuntimeLocal: compute handler returned, result=%s", self._result.value
        )

    # ------------------------------------------------------------------
    # Event bus construction
    # ------------------------------------------------------------------

    def _create_event_bus(self) -> ProtocolLocalRuntimeBus:
        """Construct the event bus implementation requested by ``backend_overrides``.

        Default behavior (no override or explicit ``event_bus=inmemory``)
        returns ``EventBusInmemory(environment="local", group="runtime-local")``
        — identical to the pre-OMN-9776 hardcoded path.

        When ``backend_overrides['event_bus'] == 'kafka'``, the bus class is
        discovered via the ``onex.backends`` entry-point group (omnibase_infra
        registers ``event_bus_kafka`` there). This indirection is mandatory:
        omnibase_core cannot import omnibase_infra directly (compat→core→spi→infra
        layering, enforced by sdk-boundary-check CI).

        The Kafka bus is instantiated through its provider factory. When
        ``backend_overrides['kafka_bootstrap']`` is supplied, RuntimeLocal asks
        the provider factory to construct from the bootstrap override and does
        not mutate process environment.

        Any other value (``"kafak"``, ``"redis"``, etc.) is rejected up-front:
        silent fallback to in-memory hides typos and misconfigured stacks, and
        running with the wrong backend is a far more dangerous failure mode
        than a clear startup error.

        Raises:
            ModelOnexError: If ``event_bus`` is set to a value not in
                ``SUPPORTED_EVENT_BUS_VALUES``. Also raised if ``event_bus=kafka``
                is requested but the ``onex.backends:event_bus_kafka`` entry
                point is not installed or fails to load — fail-fast rather
                than silently downgrading to in-memory.
        """
        bus_kind = self.backend_overrides.get("event_bus", "inmemory")

        if bus_kind not in SUPPORTED_EVENT_BUS_VALUES:
            sorted_values = ", ".join(sorted(SUPPORTED_EVENT_BUS_VALUES))
            msg = (
                f"Unsupported backend override event_bus={bus_kind!r}. "
                f"Supported values: {sorted_values}."
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                message=msg,
            )

        if bus_kind == "kafka":
            return self._create_kafka_event_bus()

        from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory

        bus = EventBusInmemory(environment="local", group="runtime-local")
        logger.info("RuntimeLocal: event bus selected (inmemory)")
        return cast("ProtocolLocalRuntimeBus", bus)

    def _create_kafka_event_bus(self) -> ProtocolLocalRuntimeBus:
        """Discover and instantiate the Kafka event bus via entry points.

        The provider (omnibase_infra) registers
        ``event_bus_kafka = "omnibase_infra.event_bus.event_bus_kafka:EventBusKafka"``
        under the ``onex.backends`` group. We look it up by name, instantiate
        through ``EventBusKafka.default()`` for the default path. When
        ``kafka_bootstrap`` is provided, the provider's ``from_bootstrap``
        factory builds the bus from the bootstrap string so no process-wide
        environment mutation is needed.

        omnibase_core MUST NOT name any omnibase_infra symbol on any path
        (compat→core→spi→infra layering, enforced by sdk-boundary-check CI).
        The bootstrap override is therefore routed entirely through the
        entry-point-loaded provider class via its ``from_bootstrap`` factory —
        core never imports the provider's config model.
        """
        backend_eps = importlib.metadata.entry_points().select(
            group=_BACKEND_ENTRY_POINT_GROUP
        )

        kafka_ep = next(
            (ep for ep in backend_eps if ep.name == _KAFKA_EVENT_BUS_ENTRY_POINT),
            None,
        )
        if kafka_ep is None:
            msg = (
                "Requested event_bus=kafka but no entry point named "
                f"'{_KAFKA_EVENT_BUS_ENTRY_POINT}' is registered under "
                f"'{_BACKEND_ENTRY_POINT_GROUP}'. Install omnibase-infra to "
                "provide EventBusKafka."
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                message=msg,
            )

        try:
            bus_cls = kafka_ep.load()
        except (ImportError, AttributeError, ModuleNotFoundError) as exc:
            msg = (
                f"Failed to load Kafka event bus entry point "
                f"'{_KAFKA_EVENT_BUS_ENTRY_POINT}' from "
                f"'{_BACKEND_ENTRY_POINT_GROUP}': {exc}"
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                message=msg,
            ) from exc

        bootstrap_override = self.backend_overrides.get("kafka_bootstrap")
        if bootstrap_override is not None:
            # Route the bootstrap override through the provider's from_bootstrap
            # factory. Core never names an omnibase_infra symbol — the provider
            # owns its own config model construction (Phase 3a adds
            # EventBusKafka.from_bootstrap infra-side, OMN-13445).
            from_bootstrap_factory = getattr(bus_cls, "from_bootstrap", None)
            if not callable(from_bootstrap_factory):
                msg = (
                    f"Kafka event bus class {bus_cls!r} has no from_bootstrap() "
                    "factory; cannot apply kafka_bootstrap override from "
                    "RuntimeLocal. The onex.backends provider must expose "
                    "from_bootstrap(bootstrap: str) to accept the override."
                )
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    message=msg,
                )
            bus = from_bootstrap_factory(bootstrap_override)
        else:
            default_factory = getattr(bus_cls, "default", None)
            if not callable(default_factory):
                msg = (
                    f"Kafka event bus class {bus_cls!r} has no default() factory; "
                    "cannot construct from RuntimeLocal."
                )
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    message=msg,
                )
            bus = default_factory()

        logger.info(
            "RuntimeLocal: event bus selected (kafka, bootstrap=%s)",
            bootstrap_override or "<provider-default>",
        )
        return cast("ProtocolLocalRuntimeBus", bus)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run_async(self) -> EnumWorkflowResult:
        """Execute the workflow asynchronously.

        Returns:
            The terminal result state.
        """
        # 1. Load contract
        self._contract = load_workflow_contract(self.workflow_path)

        terminal_topic = self._contract.get("terminal_event")

        # Contracts without terminal_event can still be executed if they
        # declare a handler (via handler_routing.default_handler or
        # top-level handler.module/class).
        if not terminal_topic:
            if self._resolve_handler_spec() is not None:
                logger.info(
                    "RuntimeLocal: no terminal_event but handler found — "
                    "using compute execution path"
                )
                try:
                    await self._run_compute()
                except ModelOnexError:
                    self._result = EnumWorkflowResult.FAILED
                except Exception:  # fallback-ok: runtime records FAILED workflow result instead of raising to CLI
                    logger.exception(
                        "RuntimeLocal: unhandled exception during compute execution"
                    )
                    self._result = EnumWorkflowResult.FAILED
                finally:
                    self._write_state()
                logger.info("RuntimeLocal: result=%s", self._result.value)
                return self._result
            else:
                logger.error(
                    "Workflow contract missing 'terminal_event' topic "
                    "and no handler spec found (need handler_routing.default_handler "
                    "or handler.module/class)."
                )
                return EnumWorkflowResult.FAILED

        terminal_topic_name = str(terminal_topic)
        logger.info(
            "RuntimeLocal: loaded contract %s, terminal_event=%s",
            self.workflow_path.name,
            terminal_topic_name,
        )

        # 2. Create event bus per backend_overrides (default: in-memory).
        bus = self._create_event_bus()
        await bus.start()

        # 3. Dispatch to appropriate execution path
        try:
            if self._has_event_routing():
                logger.info(
                    "RuntimeLocal: contract declares handler_routing — "
                    "using event-driven execution path"
                )
                await self._run_event_driven(bus)
            else:
                logger.info(
                    "RuntimeLocal: no handler_routing — "
                    "using single-handler execution path"
                )
                await self._run_single_handler(bus, terminal_topic_name)
        except ModelOnexError:
            self._result = EnumWorkflowResult.FAILED
        except (
            Exception
        ):  # fallback-ok: runtime records FAILED workflow result and writes state
            logger.exception("RuntimeLocal: unhandled exception during execution")
            self._result = EnumWorkflowResult.FAILED
        finally:
            await bus.close()
            self._write_state()

        logger.info("RuntimeLocal: result=%s", self._result.value)
        return self._result

    @staticmethod
    def _inject_missing_run_identity(
        model_cls: type[BaseModel], raw: dict[str, object]
    ) -> dict[str, object]:
        """Inject runtime-owned defaults for required run-identity fields absent from raw.

        Mirrors the no-input-file auto-fill branch (OMN-13591): for any required
        field declared on *model_cls* that is missing from *raw*, synthesise a sensible
        runtime-owned default so the strict ``model_cls(**raw)`` call succeeds.

        Rules:
        - ``uuid.UUID`` → fresh ``uuid.uuid4()``
        - ``datetime`` → ``datetime.now(UTC)``
        - ``str`` → ``YYYYMMDD-HHMMSS-<random6>`` (satisfies ``min_length=1`` and
          common ``[A-Za-z0-9._-]+`` patterns used by run-id fields)

        Caller-supplied values are never overwritten — this is injection of defaults
        only for absent keys.  Non-UUID, non-datetime, non-str required fields are
        left for the model validator to reject with a clear error.

        Returns a new dict (does not mutate *raw*).
        """
        import typing
        from datetime import UTC
        from datetime import datetime as _dt

        # Fast path: if the raw dict already provides every field return it unchanged.
        missing_required = {
            name
            for name, fi in model_cls.model_fields.items()
            if fi.is_required() and name not in raw
        }
        if not missing_required:
            return raw

        injected: dict[str, object] = dict(raw)
        now = _dt.now(UTC)
        # Timestamp slug: YYYYMMDD-HHMMSS-<6-char hex> — satisfies min_length=1
        # and the [A-Za-z0-9._-]+ pattern common on run-id fields (OMN-13591).
        run_id_slug = f"{now:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"

        for field_name in missing_required:
            ann = model_cls.model_fields[field_name].annotation
            # Unwrap Optional[X] / X | None → resolve the inner type.
            origin = typing.get_origin(ann)
            args = typing.get_args(ann)
            if origin is typing.Union and type(None) in args:
                # Optional field — runtime does not inject; let the model handle it.
                continue
            if ann is uuid.UUID:
                injected[field_name] = uuid.uuid4()
            elif ann is _dt:
                injected[field_name] = now
            elif ann is str:
                injected[field_name] = run_id_slug
            # Other types: leave absent; model validation will report the gap.

        logger.debug(
            "RuntimeLocal: injected run-identity defaults for missing required fields "
            "%s on %s.%s (OMN-13591)",
            sorted(set(injected) - set(raw)),
            model_cls.__module__,
            model_cls.__name__,
        )
        return injected

    def _build_initial_payload(self, input_spec: RawWorkflowMap) -> object | None:
        """Import and instantiate the input model from the contract's input spec.

        Resolution order:
            1. If ``self.input_path`` is set, load JSON from that file and validate
               against the imported input model class.
            2. Otherwise instantiate the model with defaults (auto-fill required
               UUID, datetime, str, tuple, and list fields as appropriate).
            3. Return None if the input spec lacks module/class.
        """
        model_module = str(input_spec.get("module", ""))
        model_class = str(input_spec.get("class", ""))
        if not model_module or not model_class:
            return None
        try:
            mod = importlib.import_module(model_module)
            cls: type[BaseModel] = cast("type[BaseModel]", getattr(mod, model_class))
        except (ImportError, AttributeError) as exc:
            logger.warning(
                "RuntimeLocal: could not import input model %s.%s: %s",
                model_module,
                model_class,
                exc,
            )
            return None

        # Prefer --input file over defaults when provided (OMN-8938).
        if self.input_path is not None:
            try:
                raw: object = json.loads(self.input_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                msg = f"Invalid input payload at {self.input_path}: {exc}"
                logger.exception("RuntimeLocal: %s", msg)
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.INVALID_INPUT,
                    message=msg,
                ) from exc
            try:
                # OMN-13591: inject runtime-owned run-identity for required fields
                # that are absent from the caller-supplied input file, mirroring
                # the no-input-file auto-fill branch so all dispatch paths are
                # consistent. Caller-supplied values are never overwritten.
                if isinstance(raw, dict):
                    raw = self._inject_missing_run_identity(cls, raw)
                    return cls(**raw)
                return cls.model_validate(raw)
            except (TypeError, ValueError) as exc:
                msg = (
                    f"Input payload at {self.input_path} does not validate against "
                    f"{model_module}.{model_class}: {exc}"
                )
                logger.exception("RuntimeLocal: %s", msg)
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                ) from exc

        try:
            return cls()
        except (TypeError, ValueError):
            # Auto-fill required UUID and datetime fields with defaults.
            import typing
            from datetime import UTC
            from datetime import datetime as _dt

            defaults: RawWorkflowMap = {}
            for field_name, field_info in cls.model_fields.items():
                if field_info.is_required():
                    ann = field_info.annotation
                    if ann is uuid.UUID:
                        defaults[field_name] = uuid.uuid4()
                    elif ann is _dt:
                        defaults[field_name] = _dt.now(UTC)
                    elif ann is str:
                        defaults[field_name] = ""
                    else:
                        # Handle tuple[T, ...] and list[T] with empty default
                        origin = typing.get_origin(ann)
                        if origin is tuple or origin is list:
                            defaults[field_name] = ()
            try:  # fallback-ok: retry with synthesized required-field defaults for local runtime input
                return cls(**defaults)
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "RuntimeLocal: could not build input payload from %s.%s: %s",
                    model_module,
                    model_class,
                    exc,
                )
                return None

    @staticmethod
    def _result_field(result_obj: object, field_name: str) -> object | None:
        """Read a status/error field from dict-style or attribute-style envelopes."""
        if isinstance(result_obj, Mapping):
            return result_obj.get(field_name)
        return getattr(result_obj, field_name, None)

    @staticmethod
    def _classify_result(result_obj: object | None) -> EnumWorkflowResult:
        """Inspect a handler return value to determine success or failure.

        A handler that *returns* an error-shaped envelope — rather than raising —
        must still be classified FAILED. Effect/reducer handlers never raise from
        ``execute()``; they return a response with ``status="error"`` and an
        ``error_message`` (e.g. the "Handler not initialized" or a downstream
        connection failure). Before OMN-14298 only ``status == "failure"`` was
        detected, so those runs surfaced a false-green COMPLETED / exit 0.

        Decision order:
        1. ``None`` → COMPLETED (compute handlers that return nothing succeeded).
        2. positive ``cycles_failed`` → FAILED.
        3. ``status`` in :data:`_FAILURE_STATUS_VALUES` → FAILED.
        4. ``status`` in :data:`_SUCCESS_STATUS_VALUES` → COMPLETED (an explicit
           success — notably ``no_results`` — short-circuits the heuristic below).
        5. a populated ``error_message`` / ``error`` string → FAILED.
        6. otherwise → COMPLETED.
        """
        if result_obj is None:
            return EnumWorkflowResult.COMPLETED
        # Check for common failure indicators on result objects
        cycles_failed = RuntimeLocal._result_field(result_obj, "cycles_failed")
        if isinstance(cycles_failed, int | float) and cycles_failed > 0:
            return EnumWorkflowResult.FAILED
        status = RuntimeLocal._result_field(result_obj, "status")
        if isinstance(status, str):
            normalized = status.strip().lower()
            if normalized in _FAILURE_STATUS_VALUES:
                return EnumWorkflowResult.FAILED
            if normalized in _SUCCESS_STATUS_VALUES:
                return EnumWorkflowResult.COMPLETED
        # No decisive status — a populated error message/attribute is an
        # unambiguous failure signal even when the handler omits a status field.
        for attr_name in ("error_message", "error"):
            value = RuntimeLocal._result_field(result_obj, attr_name)
            if isinstance(value, str) and value.strip():
                return EnumWorkflowResult.FAILED
        return EnumWorkflowResult.COMPLETED

    def _write_state(self) -> None:
        """Serialize workflow result to ``state_root/workflow_result.json``."""
        self.state_root.mkdir(parents=True, exist_ok=True)
        result_path = self.state_root / "workflow_result.json"
        data: RawWorkflowMap = {
            "result": self._result.value,
            "exit_code": self.exit_code,
            "workflow": str(self.workflow_path),
        }
        if self._terminal_payload is not None:
            data["terminal_payload"] = self._terminal_payload
        if self._handler_result is not None:
            try:
                if hasattr(self._handler_result, "model_dump"):
                    dump_model: ProtocolLocalRuntimeDumpModel = cast(
                        "ProtocolLocalRuntimeDumpModel", self._handler_result
                    )
                    data["handler_result"] = dump_model.model_dump(mode="json")
                else:
                    serialized = json.loads(
                        json.dumps(self._handler_result, default=repr)
                    )
                    data["handler_result"] = serialized
            except (TypeError, ValueError, OverflowError):
                # fallback-ok: persist a best-effort representation when the
                # handler result cannot be fully serialized to JSON.
                data["handler_result"] = repr(self._handler_result)
        result_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("RuntimeLocal: wrote state to %s", result_path)

    def run(self) -> EnumWorkflowResult:
        """Execute the workflow synchronously (convenience wrapper).

        Returns:
            The terminal result state.
        """
        return asyncio.run(self.run_async())

    @property
    def exit_code(self) -> int:
        """CLI exit code corresponding to the current result."""
        return _exit_code_for(self._result)

    @property
    def last_error(self) -> str | None:
        """Human-readable description of the failure that ended the run, if any.

        Set when a wired handler fails or a routing/boot error aborts the run;
        ``None`` on a clean completion. Consumed by the ``onex node`` CLI to
        populate the ``SkillRoutingError`` envelope on non-zero exit (OMN-8724).
        """
        return self._last_error

    @property
    def handler_result(self) -> object | None:
        """The terminal handler's result object, if the run produced one.

        Receipt mode (OMN-13094) uses the concrete type of this object as
        the receipt's ``result_model`` schema identity; the JSON-serialized
        form lives in ``workflow_result.json`` under ``handler_result``.
        """
        return self._handler_result

    # Prevent resource leaks — reserved for future bus/container teardown.
    del_alias = None  # placeholder for __del__ if needed
