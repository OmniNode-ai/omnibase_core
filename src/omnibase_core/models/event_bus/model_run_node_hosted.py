# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Host one node in this process for ``onex run-node`` and refuse a run whose events went nowhere (OMN-25564).

``onex run-node`` hosts a node whose overlay declares ``type: inmemory`` on the in-memory bus and
``RuntimeLocal`` settles that bus after the run: its recorded events go to the forwarder the runtime has
installed, and a settle that could not carry them is written to ``workflow_result.json`` under
``bus_reading`` as a degraded reading. That reading used to end as one stderr line and exit 0, so a run
that delivered nothing looked finished. The command now ends non-zero and names what the reading says.

The behaviour lives here and not in ``cli_run_node.py``: the canonical-file-shape ratchet lets that
baselined file only shrink.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_runtime_bus_reading import (
    ModelRuntimeBusReading,
)


class ModelRunNodeHosted:
    """Namespace of the steps that host a node on the in-memory bus for ``onex run-node``."""

    @staticmethod
    def require_delivered(node_id: str, state_root: Path) -> None:
        """Refuse a finished run whose bus reading says none of its recorded events was delivered.

        A reading that is degraded but forwarded at least one event is a partial delivery (the forwarder
        refuses the run's own command by name while it carries the events); the settle step already says so
        on stderr, and the run's answer stands.
        """
        result_path = state_root / "workflow_result.json"
        try:
            recorded = json.loads(result_path.read_text(encoding="utf-8")).get(
                "bus_reading"
            )
        except (OSError, ValueError) as exc:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Node '{node_id}' ran but its bus reading at {result_path} cannot "
                f"be read ({type(exc).__name__}), so delivery of its events is unknown.",
            ) from exc
        if recorded is None:
            return
        reading = ModelRuntimeBusReading.model_validate(recorded)
        if reading.degraded and reading.events_forwarded == 0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Node '{node_id}' ran but its recorded events were not delivered "
                f"(bus kind={reading.kind.value} recorded={reading.events_recorded} "
                f"not_delivered={reading.events_failed}): {reading.reason}",
            )

    @staticmethod
    def run(
        node_id: str, contract_path: Path, payload: dict[str, object], timeout: int
    ) -> dict[str, object]:
        """Host the node here on the in-memory bus (overlay ``type: inmemory``, OMN-22362)."""
        from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
        from omnibase_core.runtime.runtime_local import RuntimeLocal

        with tempfile.TemporaryDirectory(prefix="onex-run-node-") as scratch:
            input_path = Path(scratch) / "input.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            # The overlay declared an in-memory runtime, so the run declares event_bus=inmemory: with one
            # forwarder installed its recorded events reach the hosted bus, with none it says so (OMN-24000).
            runtime = RuntimeLocal(
                workflow_path=contract_path,
                state_root=Path(scratch) / "state",
                input_path=input_path,
                timeout=timeout,
                backend_overrides={"event_bus": "inmemory"},
            )
            result = runtime.run()
            if result is not EnumWorkflowResult.COMPLETED:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                    message=f"Node '{node_id}' hosted in process ended {result.value}: "
                    f"{runtime.last_error or 'no error recorded'}",
                )
            ModelRunNodeHosted.require_delivered(node_id, Path(scratch) / "state")
        produced = runtime.handler_result
        if isinstance(produced, BaseModel):
            return produced.model_dump(mode="json")
        return dict(produced) if isinstance(produced, dict) else {"result": produced}


__all__ = ["ModelRunNodeHosted"]
