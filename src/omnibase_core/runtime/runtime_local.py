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
import inspect
import json
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.models.errors.model_onex_error import ModelOnexError

logger = logging.getLogger(__name__)

# Known backend protocol keys that --backend can override.
KNOWN_BACKEND_KEYS: frozenset[str] = frozenset(
    {"event_bus", "state_store", "metrics", "tracing"}
)


@dataclass(frozen=True)
class _ResolvedRoutingEntry:
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
) -> dict[str, Any]:
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

    return data


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

        # ONEX_EXCLUDE: dict_str_any — workflow contract raw YAML
        self._contract: dict[str, Any] = {}
        self._result: EnumWorkflowResult = EnumWorkflowResult.TIMEOUT
        self._terminal_received = asyncio.Event()

        # Diagnostic tracking: events received per topic
        self._events_received: dict[str, int] = {}
        self._last_error: str | None = None
        self._handlers_wired: list[str] = []
        self._terminal_payload: dict[str, Any] | None = None
        self._handler_result: Any = None

    # ONEX_EXCLUDE: dict_str_any — event bus payload
    def _on_terminal_event(self, payload: dict[str, Any]) -> None:
        """Callback invoked when a message arrives on the terminal_event topic."""
        self._record_event("(terminal)")
        if self._terminal_received.is_set():
            logger.warning("Duplicate terminal event received — ignoring (first wins).")
            return

        status = payload.get("status", "success")
        logger.info("RuntimeLocal: terminal event received (status=%s)", status)
        self._terminal_payload = payload
        if status == "failure":
            self._result = EnumWorkflowResult.FAILED
        else:
            self._result = EnumWorkflowResult.COMPLETED

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

    # ------------------------------------------------------------------
    # Handler instantiation (shared helper)
    # ------------------------------------------------------------------

    # ENV_VAR_KWARG_MAP maps constructor parameter names to environment
    # variable names so that handler classes can receive secrets without
    # hard-coding os.environ lookups.
    _ENV_VAR_KWARG_MAP: dict[str, str] = {
        "linear_api_key": "LINEAR_API_KEY",  # pragma: allowlist secret
    }

    def _instantiate_handler(self, module_name: str, class_name: str) -> Any:
        """Import *module_name*, resolve *class_name*, and return an instance.

        Constructor kwargs are auto-populated from environment variables when the
        parameter name appears in ``_ENV_VAR_KWARG_MAP`` and the corresponding
        env var is set.

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

        # Inspect constructor for env-var kwargs
        kwargs: dict[str, str] = {}
        try:
            sig = inspect.signature(handler_cls.__init__)
            for param_name in sig.parameters:
                if param_name == "self":
                    continue
                env_var = self._ENV_VAR_KWARG_MAP.get(param_name)
                if env_var is not None:
                    value = os.environ.get(env_var)
                    if value is not None:
                        kwargs[param_name] = value
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
        self, handler_instance: Any, class_name: str
    ) -> tuple[Any, str]:
        """Resolve the entry method on a handler instance.

        Prefers ``handle()``. If absent, tries ``run_full_cycle``, ``run``,
        ``execute`` in order. Returns ``(method, name)`` or ``(None, "")``
        if no callable entry point is found.
        """
        handle_method = getattr(handler_instance, "handle", None)
        if handle_method is not None:
            return handle_method, "handle"

        for name in self._FALLBACK_METHODS:
            method = getattr(handler_instance, name, None)
            if method is not None and callable(method):
                logger.info(
                    "RuntimeLocal: handler %s has no handle() — falling back to %s()",
                    class_name,
                    name,
                )
                return method, name

        logger.error(
            "Handler %s has no handle(), run_full_cycle(), run(), or execute() method",
            class_name,
        )
        return None, ""

    async def _invoke_handler_method(
        self,
        method: Any,
        method_name: str,
        handler_instance: Any,
        initial_payload: Any,
    ) -> Any:
        """Invoke a handler method, adapting the call signature as needed.

        ``handle()`` receives a single positional payload argument.
        ``run_full_cycle()`` receives a typed command model as its first arg.
        ``run()`` and ``execute()`` are tried with payload first, then without.
        """
        try:
            if asyncio.iscoroutinefunction(method):
                result = await method(initial_payload)
            else:
                result = method(initial_payload)
        except TypeError as original_exc:
            # The method may not accept arguments (e.g. run() with no args).
            # Retry without args; if that also fails, re-raise the original.
            try:
                if asyncio.iscoroutinefunction(method):
                    result = await method()
                else:
                    result = method()
            except TypeError:
                raise original_exc from None

        # run_full_cycle returns (state, events, completed_event) — extract
        # the completed event for result classification.
        if isinstance(result, tuple) and len(result) >= 3:
            result = result[-1]

        return result

    # ------------------------------------------------------------------
    # Single-handler execution path
    # ------------------------------------------------------------------

    async def _run_single_handler(self, bus: Any, terminal_topic: str) -> None:
        """Resolve and invoke the single handler declared in the contract.

        If the handler returns a result directly, it is classified immediately.
        Otherwise (e.g. handler publishes to the bus and the terminal event
        arrives asynchronously), the method waits up to ``self.timeout`` seconds
        for the terminal event.

        The terminal topic subscription is owned by this method (not
        ``run_async``) so that event-driven workflows—which subscribe to
        terminal topics via ``publish_topics``—don't receive duplicates.
        """

        async def _on_terminal_msg(msg: Any) -> None:
            """Adapt async bus callback to sync terminal handler."""
            payload = json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            self._on_terminal_event(payload)

        await bus.subscribe(
            terminal_topic,
            on_message=_on_terminal_msg,
            group_id="runtime-local-terminal",
        )
        logger.info("RuntimeLocal: subscribed to terminal topic '%s'", terminal_topic)

        handler_spec = self._contract.get("handler", {})
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

        self._handlers_wired = [f"{handler_module_name}.{handler_class_name}"]

        handler_instance = self._instantiate_handler(
            handler_module_name, handler_class_name
        )

        # Build initial payload from handler or contract input spec.
        # input_model may be a dotted string ("module.ClassName") — coerce to dict.
        input_spec: dict[str, Any] | str = handler_spec.get(
            "input_model", {}
        ) or self._contract.get("input", {})
        if isinstance(input_spec, str) and "." in input_spec:
            module_name, class_name = input_spec.rsplit(".", 1)
            input_spec = {"module": module_name, "class": class_name}
        elif not isinstance(input_spec, dict):
            input_spec = {}
        initial_payload = self._build_initial_payload(input_spec)

        # Invoke handler — prefer handle(), fall back to run_full_cycle/run/execute
        handle_method, method_name = self._resolve_handler_method(
            handler_instance, handler_class_name
        )
        if handle_method is None:
            self._result = EnumWorkflowResult.FAILED
            return

        result_obj = await self._invoke_handler_method(
            handle_method, method_name, handler_instance, initial_payload
        )

        # If the handler returned a result, use it directly — don't wait for
        # terminal event since single-handler workflows return synchronously.
        # If terminal_received is already set (e.g. by _on_terminal_event with a
        # failure), preserve that result rather than overwriting with a classification
        # of None.
        if result_obj is not None:
            self._handler_result = result_obj
            self._result = self._classify_result(result_obj)
            await self._publish_synthesized_terminal(bus, terminal_topic)
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
                correlation_id = self._contract.get("correlation_id", "unknown")
                logger.warning(
                    "RuntimeLocal: timeout (%ds) waiting for terminal event "
                    "[correlation_id=%s]",
                    self.timeout,
                    correlation_id,
                )
                self._result = EnumWorkflowResult.TIMEOUT
                self._log_timeout_summary()
                return

        logger.info("RuntimeLocal: handler returned, result=%s", self._result.value)

    async def _publish_synthesized_terminal(
        self, bus: Any, terminal_topic: str
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
                    "correlation_id": str(uuid.uuid4()),
                    "source": "runtime_local",
                }
            ).encode("utf-8"),
        )

    # ------------------------------------------------------------------
    # Event-driven execution path
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_handler_input_topic(
        entry: dict[str, Any],
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
        routing: dict[str, Any],
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
        handlers: list[dict[str, Any]] = routing.get("handlers", [])
        errors: list[str] = []
        input_topic_set = set(subscribe_topics)

        # Per-entry field and topic validation
        for i, entry in enumerate(handlers):
            prefix = f"handlers[{i}]"
            em = entry.get("event_model", {})
            hd = entry.get("handler", {})
            if not em.get("name"):
                errors.append(f"{prefix}.event_model.name is missing")
            if not em.get("module"):
                errors.append(f"{prefix}.event_model.module is missing")
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
            e.get("event_model", {}).get("name")
            for e in handlers
            if e.get("event_model", {}).get("name")
        }
        for i, entry in enumerate(handlers):
            prefix = f"handlers[{i}]"
            for out_evt in entry.get("output_events", []):
                if out_evt not in known_event_names and not publish_topics:
                    errors.append(
                        f"{prefix}.output_events entry '{out_evt}' does not "
                        f"match any downstream handler event_model.name and "
                        f"no publish_topics defined for terminal output"
                    )

        return errors

    def _resolve_routing_entries(
        self,
        routing: dict[str, Any],
        subscribe_topics: list[str],
        publish_topics: list[str],
    ) -> list[_ResolvedRoutingEntry]:
        """Build resolved routing entries with concrete input/output topics."""
        handlers: list[dict[str, Any]] = routing.get("handlers", [])

        # Build index: event_model.name -> subscribe_topics index
        name_to_topic_idx: dict[str, int] = {}
        for i, entry in enumerate(handlers):
            em_name = entry.get("event_model", {}).get("name", "")
            if em_name:
                name_to_topic_idx[em_name] = i

        resolved: list[_ResolvedRoutingEntry] = []
        for i, entry in enumerate(handlers):
            em = entry.get("event_model", {})
            hd = entry.get("handler", {})
            output_events = entry.get("output_events", [])

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

            # Terminal reducers may have no input topic (no positional slot and
            # no explicit subscribe_topic) — use empty string to skip bus wiring.
            input_topic = (
                self._resolve_handler_input_topic(entry, i, subscribe_topics) or ""
            )

            resolved.append(
                _ResolvedRoutingEntry(
                    handler_module=hd.get("module", ""),
                    handler_class=hd.get("name", ""),
                    handler_name=hd.get("name", "unknown"),
                    event_model_module=em.get("module", ""),
                    event_model_class=em.get("name", ""),
                    input_topic=input_topic,
                    output_topic=output_topic,
                )
            )

        return resolved

    async def _run_event_driven(self, bus: Any) -> None:
        """Execute the workflow using event-driven handler routing.

        Reads handler_routing.handlers from the contract, validates the
        routing graph, wires HandlerBusAdapters to the in-memory event bus,
        publishes the initial command, and awaits the terminal event.
        """
        from omnibase_core.runtime.runtime_local_adapter import HandlerBusAdapter

        routing: dict[str, Any] = self._contract.get("handler_routing", {})
        event_bus_spec: dict[str, Any] = self._contract.get("event_bus", {})
        subscribe_topics: list[str] = event_bus_spec.get("subscribe_topics", [])
        publish_topics: list[str] = event_bus_spec.get("publish_topics", [])

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
        unsubscribe_handles: list[Any] = []
        self._handlers_wired = [e.handler_name for e in resolved_entries]

        def _fail_callback() -> None:
            self._result = EnumWorkflowResult.FAILED
            self._terminal_received.set()

        for entry in resolved_entries:
            handler_instance = self._instantiate_handler(
                entry.handler_module, entry.handler_class
            )

            # Import the input model class
            try:
                em_mod = importlib.import_module(entry.event_model_module)
                input_model_cls = getattr(em_mod, entry.event_model_class)
            except (ImportError, AttributeError) as exc:
                msg = (
                    f"Failed to resolve event model "
                    f"{entry.event_model_module}.{entry.event_model_class}: {exc}"
                )
                logger.exception("RuntimeLocal: %s", msg)
                self._result = EnumWorkflowResult.FAILED
                return

            def _make_fail_cb(name: str) -> Any:
                def _cb() -> None:
                    self._last_error = f"handler '{name}' failed"
                    _fail_callback()

                return _cb

            adapter = HandlerBusAdapter(
                handler=handler_instance,
                handler_name=entry.handler_name,
                input_model_cls=input_model_cls,
                output_topic=entry.output_topic or None,
                bus=bus,
                on_error=_make_fail_cb(entry.handler_name),
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

        # --- 5. Subscribe to terminal (publish) topics ---
        async def _on_terminal_msg(msg: Any) -> None:
            payload = json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            self._on_terminal_event(payload)

        for pub_topic in publish_topics:
            unsub = await bus.subscribe(
                pub_topic,
                on_message=_on_terminal_msg,
                group_id="runtime-local-terminal",
            )
            unsubscribe_handles.append(unsub)

        # --- 6. Build and publish initial payload ---
        correlation_id = uuid.uuid4()
        # ONEX_EXCLUDE: dict_str_any — input_model can be dict or dotted string
        raw_input_spec: Any = self._contract.get("input_model", {})

        # input_model can be a string "module.Class" or a dict with module/class
        initial_payload = None
        if isinstance(raw_input_spec, str) and "." in raw_input_spec:
            # Format: "some.module.ClassName"
            parts = raw_input_spec.rsplit(".", 1)
            initial_payload = self._build_initial_payload(
                {"module": parts[0], "class": parts[1]}
            )
        elif isinstance(raw_input_spec, dict):
            initial_payload = self._build_initial_payload(raw_input_spec)

        if initial_payload is not None:
            # Inject correlation_id if the model supports it
            if hasattr(initial_payload, "correlation_id"):
                try:
                    initial_payload.correlation_id = correlation_id
                except (AttributeError, ValueError):
                    pass  # frozen model or incompatible type

            await bus.publish(
                subscribe_topics[0],
                None,
                initial_payload.model_dump_json().encode("utf-8"),
            )
        else:
            # Publish a minimal payload with just the correlation_id
            minimal = json.dumps({"correlation_id": str(correlation_id)}).encode(
                "utf-8"
            )
            await bus.publish(subscribe_topics[0], None, minimal)

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
        handler_spec = self._contract.get("handler", {})
        input_spec_raw: dict[str, Any] | str = (
            handler_spec.get("input_model", {})
            if isinstance(handler_spec, dict)
            else {}
        ) or self._contract.get("input", {})
        if isinstance(input_spec_raw, str) and "." in input_spec_raw:
            if not all(seg.isidentifier() for seg in input_spec_raw.split(".")):
                logger.warning(
                    "RuntimeLocal: invalid input_model format: %s",
                    input_spec_raw,
                )
                input_spec: dict[str, Any] = {}
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

        self._result = self._classify_result(result_obj)
        logger.info(
            "RuntimeLocal: compute handler returned, result=%s", self._result.value
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run_async(self) -> EnumWorkflowResult:
        """Execute the workflow asynchronously.

        Returns:
            The terminal result state.
        """
        # TEST-ONLY PLUMBING: exposes state_root to test fixture handlers
        # (e.g. HandlerProofNoop). Production handlers MUST NOT read
        # ONEX_STATE_ROOT — they receive state via ProtocolStateStore DI.
        # See OMN-8938 plan Task 3 Step 6.
        os.environ["ONEX_STATE_ROOT"] = str(self.state_root)

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
                except Exception:
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

        logger.info(
            "RuntimeLocal: loaded contract %s, terminal_event=%s",
            self.workflow_path.name,
            terminal_topic,
        )

        # 2. Create in-memory event bus
        from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory

        bus = EventBusInmemory(environment="local", group="runtime-local")
        await bus.start()
        logger.info("RuntimeLocal: event bus started (inmemory)")

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
                await self._run_single_handler(bus, terminal_topic)
        except ModelOnexError:
            self._result = EnumWorkflowResult.FAILED
        except Exception:
            logger.exception("RuntimeLocal: unhandled exception during execution")
            self._result = EnumWorkflowResult.FAILED
        finally:
            await bus.close()
            self._write_state()

        logger.info("RuntimeLocal: result=%s", self._result.value)
        return self._result

    # ONEX_EXCLUDE: dict_str_any — input spec from workflow contract
    def _build_initial_payload(self, input_spec: dict[str, Any]) -> Any:
        """Import and instantiate the input model from the contract's input spec.

        Resolution order:
            1. If ``self.input_path`` is set, load JSON from that file and validate
               against the imported input model class.
            2. Otherwise instantiate the model with defaults (auto-fill required
               UUID, datetime, str, tuple, and list fields as appropriate).
            3. Return None if the input spec lacks module/class.
        """
        model_module = input_spec.get("module", "")
        model_class = input_spec.get("class", "")
        if not model_module or not model_class:
            return None
        try:
            mod = importlib.import_module(model_module)
            cls = getattr(mod, model_class)
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
                raw = json.loads(self.input_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                msg = f"Invalid input payload at {self.input_path}: {exc}"
                logger.exception("RuntimeLocal: %s", msg)
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.INVALID_INPUT,
                    message=msg,
                ) from exc
            try:
                if isinstance(raw, dict):
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

            defaults: dict[str, Any] = {}
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
            try:
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
    def _classify_result(result_obj: Any) -> EnumWorkflowResult:
        """Inspect handler return value to determine success or failure."""
        if result_obj is None:
            return EnumWorkflowResult.COMPLETED
        # Check for common failure indicators on result objects
        cycles_failed = getattr(result_obj, "cycles_failed", None)
        if cycles_failed is not None and cycles_failed > 0:
            return EnumWorkflowResult.FAILED
        status = getattr(result_obj, "status", None)
        if status == "failure":
            return EnumWorkflowResult.FAILED
        return EnumWorkflowResult.COMPLETED

    def _write_state(self) -> None:
        """Serialize workflow result to ``state_root/workflow_result.json``."""
        self.state_root.mkdir(parents=True, exist_ok=True)
        result_path = self.state_root / "workflow_result.json"
        data: dict[str, Any] = {
            "result": self._result.value,
            "exit_code": self.exit_code,
            "workflow": str(self.workflow_path),
        }
        if self._terminal_payload is not None:
            data["terminal_payload"] = self._terminal_payload
        if self._handler_result is not None:
            try:
                if hasattr(self._handler_result, "model_dump"):
                    data["handler_result"] = self._handler_result.model_dump(
                        mode="json"
                    )
                else:
                    serialized = json.loads(
                        json.dumps(self._handler_result, default=repr)
                    )
                    data["handler_result"] = serialized
            except (TypeError, ValueError, OverflowError):
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

    # Prevent resource leaks — reserved for future bus/container teardown.
    del_alias = None  # placeholder for __del__ if needed
