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
        timeout: int = 300,
    ) -> None:
        self.workflow_path = workflow_path
        self.state_root = state_root
        self.backend_overrides = backend_overrides or {}
        self.timeout = timeout

        # ONEX_EXCLUDE: dict_str_any — workflow contract raw YAML
        self._contract: dict[str, Any] = {}
        self._result: EnumWorkflowResult = EnumWorkflowResult.TIMEOUT
        self._terminal_received = asyncio.Event()

        # Diagnostic tracking: events received per topic
        self._events_received: dict[str, int] = {}
        self._last_error: str | None = None
        self._handlers_wired: list[str] = []

    # ONEX_EXCLUDE: dict_str_any — event bus payload
    def _on_terminal_event(self, payload: dict[str, Any]) -> None:
        """Callback invoked when a message arrives on the terminal_event topic."""
        self._record_event("(terminal)")
        if self._terminal_received.is_set():
            logger.warning("Duplicate terminal event received — ignoring (first wins).")
            return

        status = payload.get("status", "success")
        logger.info("RuntimeLocal: terminal event received (status=%s)", status)
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
        self._handlers_wired = [f"{handler_module_name}.{handler_class_name}"]

        if not handler_module_name or not handler_class_name:
            logger.error("Workflow contract missing handler.module or handler.class")
            self._result = EnumWorkflowResult.FAILED
            return

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

        # Invoke handler
        handle_method = getattr(handler_instance, "handle", None)
        if handle_method is None:
            logger.error("Handler %s has no handle() method", handler_class_name)
            self._result = EnumWorkflowResult.FAILED
            return

        if asyncio.iscoroutinefunction(handle_method):
            result_obj = await handle_method(initial_payload)
        else:
            result_obj = handle_method(initial_payload)

        # If the handler returned a result, use it directly — don't wait for
        # terminal event since single-handler workflows return synchronously.
        # If terminal_received is already set (e.g. by _on_terminal_event with a
        # failure), preserve that result rather than overwriting with a classification
        # of None.
        if result_obj is not None:
            self._result = self._classify_result(result_obj)
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

    # ------------------------------------------------------------------
    # Event-driven execution path
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_routing(
        routing: dict[str, Any],
        subscribe_topics: list[str],
        publish_topics: list[str],
    ) -> list[str]:
        """Validate handler routing entries against topic lists.

        Returns:
            List of validation error messages (empty means valid).
        """
        handlers: list[dict[str, Any]] = routing.get("handlers", [])
        errors: list[str] = []

        # Positional alignment check
        if len(subscribe_topics) != len(handlers):
            errors.append(
                f"subscribe_topics length ({len(subscribe_topics)}) != "
                f"handlers length ({len(handlers)})"
            )

        # Per-entry field validation
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
                    output_topic = subscribe_topics[downstream_idx]
                elif publish_topics:
                    output_topic = publish_topics[0]

            resolved.append(
                _ResolvedRoutingEntry(
                    handler_module=hd.get("module", ""),
                    handler_class=hd.get("name", ""),
                    handler_name=hd.get("name", "unknown"),
                    event_model_module=em.get("module", ""),
                    event_model_class=em.get("name", ""),
                    input_topic=subscribe_topics[i],
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

    async def run_async(self) -> EnumWorkflowResult:
        """Execute the workflow asynchronously.

        Returns:
            The terminal result state.
        """
        # 1. Load contract
        self._contract = load_workflow_contract(self.workflow_path)

        terminal_topic = self._contract.get("terminal_event")
        if not terminal_topic:
            logger.error("Workflow contract missing 'terminal_event' topic.")
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

        If the input spec declares a ``module`` and ``class``, the model is imported
        and instantiated with defaults. Otherwise returns None (handler must accept
        None or have its own defaults).
        """
        model_module = input_spec.get("module", "")
        model_class = input_spec.get("class", "")
        if not model_module or not model_class:
            return None
        try:
            mod = importlib.import_module(model_module)
            cls = getattr(mod, model_class)
            try:
                return cls()
            except (TypeError, ValueError):
                # Auto-fill required UUID and datetime fields with defaults
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
                return cls(**defaults)
        except (ImportError, AttributeError, TypeError) as exc:
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
        data = {
            "result": self._result.value,
            "exit_code": self.exit_code,
            "workflow": str(self.workflow_path),
        }
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
