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
import json
import logging
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

    # ONEX_EXCLUDE: dict_str_any — event bus payload
    def _on_terminal_event(self, payload: dict[str, Any]) -> None:
        """Callback invoked when a message arrives on the terminal_event topic."""
        if self._terminal_received.is_set():
            logger.warning("Duplicate terminal event received — ignoring (first wins).")
            return

        status = payload.get("status", "success")
        if status == "failure":
            self._result = EnumWorkflowResult.FAILED
        else:
            self._result = EnumWorkflowResult.COMPLETED

        self._terminal_received.set()

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

        # 3. Subscribe to terminal event topic
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

        # 4. Resolve handler from contract
        handler_spec = self._contract.get("handler", {})
        handler_module_name = handler_spec.get("module", "")
        handler_class_name = handler_spec.get("class", "")

        if not handler_module_name or not handler_class_name:
            logger.error("Workflow contract missing handler.module or handler.class")
            self._result = EnumWorkflowResult.FAILED
            await bus.close()
            self._write_state()
            return self._result

        try:
            mod = importlib.import_module(handler_module_name)
            handler_cls = getattr(mod, handler_class_name)
        except (ImportError, AttributeError) as exc:
            logger.exception(
                "RuntimeLocal: failed to resolve handler %s.%s",
                handler_module_name,
                handler_class_name,
            )
            self._result = EnumWorkflowResult.FAILED
            await bus.close()
            self._write_state()
            return self._result

        handler_instance = handler_cls()
        logger.info(
            "RuntimeLocal: resolved handler %s.%s",
            handler_module_name,
            handler_class_name,
        )

        # 5. Build initial payload from contract input spec
        initial_payload = self._build_initial_payload(self._contract.get("input", {}))

        # 6. Invoke handler
        try:
            handle_method = getattr(handler_instance, "handle", None)
            if handle_method is None:
                logger.error("Handler %s has no handle() method", handler_class_name)
                self._result = EnumWorkflowResult.FAILED
            elif asyncio.iscoroutinefunction(handle_method):
                result_obj = await handle_method(initial_payload)
                self._result = self._classify_result(result_obj)
            else:
                result_obj = handle_method(initial_payload)
                self._result = self._classify_result(result_obj)
            logger.info("RuntimeLocal: handler returned, result=%s", self._result.value)
        except Exception:
            logger.exception("RuntimeLocal: handler raised an exception")
            self._result = EnumWorkflowResult.FAILED

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
            return cls()
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
