# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One validator run over the in-memory bus, for the golden and error chain event tests (OMN-23186)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.event_bus import event_bus_inmemory
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect import (
    handler_validator_runtime_overlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.topics import TopicBase
from omnibase_core.validation.validator_base import ValidatorBase

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]
_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_RUN_TOPIC = HandlerValidatorRuntimeOverlay().settings().run_topic


def run_on_bus(
    validator: type[ValidatorBase],
    target: Path,
    report: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, list[ModelValidatorRunEvent], list[ModelEventMessage], str]:
    """Exit code, the run events, the triggered events and the report id of one run."""
    listened: dict[str, list[ModelEventMessage]] = {"run": [], "triggered": []}

    async def _on_run(message: ModelEventMessage) -> None:
        listened["run"].append(message)

    async def _on_triggered(message: ModelEventMessage) -> None:
        listened["triggered"].append(message)

    bus = EventBusInmemory()
    asyncio.run(bus.subscribe(_RUN_TOPIC, on_message=_on_run, group_id="listener"))
    asyncio.run(
        bus.subscribe(
            str(TopicBase.VALIDATOR_TRIGGERED),
            on_message=_on_triggered,
            group_id="listener",
        )
    )
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)
    monkeypatch.chdir(ROOT)
    exit_code = main(
        validator,
        [str(target), "--report-json", str(report), "--overlay", str(_INMEMORY)],
        build_validator_container,
    )
    runs = [
        ModelValidatorRunEvent.model_validate_json(m.value) for m in listened["run"]
    ]
    written = json.loads(report.read_text(encoding="utf-8"))
    return exit_code, runs, listened["triggered"], str(written["report_id"])
