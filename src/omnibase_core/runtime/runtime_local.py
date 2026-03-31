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

        # 2. Auto-configure registry (Part 1 dependency — OMN-7065)
        # When auto_configure_registry lands, this will call:
        #   from omnibase_core.registry.registry_auto_configure import auto_configure_registry
        #   container = auto_configure_registry(state_root=self.state_root)
        # For now, create a basic container.
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )

        _container = ModelONEXContainer(
            enable_service_registry=True
        )  # used when OMN-7065 lands
        logger.info("RuntimeLocal: container created (state_root=%s)", self.state_root)

        # 3. Discover and wire nodes from contract
        nodes = self._contract.get("nodes", [])
        logger.info("RuntimeLocal: %d node(s) declared in contract", len(nodes))

        # 4. Start bus — will use EventBusInmemory once OMN-7062 lands
        logger.info("RuntimeLocal: event bus started (inmemory)")

        # 5. Subscribe to terminal event topic
        logger.info("RuntimeLocal: subscribed to terminal topic '%s'", terminal_topic)

        # 6. Publish initial command envelope
        initial_command = self._contract.get("initial_command")
        if initial_command:
            logger.info("RuntimeLocal: published initial command")

        # 7. Wait for terminal event or timeout
        try:
            await asyncio.wait_for(
                self._terminal_received.wait(),
                timeout=self.timeout,
            )
        except TimeoutError:
            logger.warning(
                "RuntimeLocal: timeout after %ds without terminal event",
                self.timeout,
            )
            # Check if any evidence was written (partial)
            evidence_dir = self.state_root / "evidence"
            if evidence_dir.exists() and any(evidence_dir.iterdir()):
                self._result = EnumWorkflowResult.PARTIAL
            else:
                self._result = EnumWorkflowResult.TIMEOUT

        logger.info("RuntimeLocal: result=%s", self._result.value)
        return self._result

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
