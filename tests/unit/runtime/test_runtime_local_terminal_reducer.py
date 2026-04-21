# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests: RuntimeLocal terminal reducer without subscribe_topics padding.

Verifies OMN-9262: the map-based _validate_routing replaces the strict
positional len(subscribe_topics)==len(handlers) check. Terminal reducers
no longer require callers to pad subscribe_topics.

TDD evidence (main branch, before this PR):
    routing with 1 subscribe_topic and 2 handlers raised:
    "subscribe_topics length (1) != handlers length (2)"
    confirming the tests in this file would have failed before the fix.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.runtime.runtime_local import RuntimeLocal


@pytest.mark.integration
def test_terminal_reducer_no_padding_validates_cleanly() -> None:
    """Map-based validator accepts terminal reducer with fewer subscribe_topics than handlers.

    Side effect: RuntimeLocal._validate_routing returns an empty list (the list
    object is mutated by the validator — observable state change from the call).

    Old positional code appended:
        "subscribe_topics length (1) != handlers length (2)"
    New map-based code: no error — second handler has no positional slot, which
    is valid for a terminal reducer (gets no bus subscription).
    """
    routing = {
        "handlers": [
            {
                "event_model": {"name": "EventA", "module": "mod.events"},
                "handler": {"name": "HandlerA", "module": "mod.handlers"},
                "output_events": [],
            },
            {
                "event_model": {"name": "EventB", "module": "mod.events"},
                "handler": {"name": "TerminalReducer", "module": "mod.handlers"},
                "output_events": [],
            },
        ]
    }
    errors = RuntimeLocal._validate_routing(
        routing,
        subscribe_topics=[
            "topic.a.v1"
        ],  # 1 topic, 2 handlers — old code raised an error
        publish_topics=[],
    )
    assert errors == [], f"Expected no errors, got: {errors}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_terminal_reducer_workflow_writes_state_to_disk(tmp_path: Path) -> None:
    """Full workflow with terminal reducer (explicit subscribe_topic) writes state to disk.

    Side effect: workflow_result.json is written to state_root/workflow_result.json.

    Topology:
        HandlerA: StartEvent -> MidEvent   (positional slot 0: cmd.tr.v1)
        HandlerB: MidEvent   -> DoneEvent  (positional slot 1: evt.tr.mid.v1)
        HandlerCTerminal: DoneEvent (explicit subscribe_topic: evt.tr.done.v1, no output)

    HandlerCTerminal uses an explicit subscribe_topic field; subscribe_topics
    does not need a dummy padding entry. Old code would have required a third
    positional entry to pass len(subscribe_topics)==len(handlers).
    """

    class StartEvent(BaseModel):
        correlation_id: str

    class MidEvent(BaseModel):
        correlation_id: str
        step: str = "mid"

    class DoneEvent(BaseModel):
        correlation_id: str
        done: bool = True

    terminal_invocations: list[str] = []

    class HandlerA:
        async def handle(self, correlation_id: str) -> MidEvent:
            return MidEvent(correlation_id=correlation_id)

    class HandlerB:
        async def handle(self, correlation_id: str, step: str) -> DoneEvent:
            return DoneEvent(correlation_id=correlation_id)

    class HandlerCTerminal:
        async def handle(self, correlation_id: str, done: bool) -> None:
            terminal_invocations.append(correlation_id)

    mod_map: dict[str, tuple[str, Any]] = {
        "_omn9262_start": ("StartEvent", StartEvent),
        "_omn9262_mid": ("MidEvent", MidEvent),
        "_omn9262_done": ("DoneEvent", DoneEvent),
        "_omn9262_ha": ("HandlerA", HandlerA),
        "_omn9262_hb": ("HandlerB", HandlerB),
        "_omn9262_hc": ("HandlerCTerminal", HandlerCTerminal),
    }
    for mod_name, (cls_name, cls) in mod_map.items():
        mod = types.ModuleType(mod_name)
        setattr(mod, cls_name, cls)
        sys.modules[mod_name] = mod

    try:
        contract_yaml = (
            "workflow_id: test_omn9262_terminal_reducer\n"
            "contract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: workflow\n"
            "description: OMN-9262 terminal reducer integration test\n"
            "initial_command: cmd.tr.v1\n"
            "terminal_event: evt.tr.done.v1\n"
            "event_bus:\n"
            "  subscribe_topics:\n"
            "    - cmd.tr.v1\n"
            "    - evt.tr.mid.v1\n"
            "    - evt.tr.done.v1\n"
            "  publish_topics:\n"
            "    - evt.tr.done.v1\n"
            "input_model:\n"
            "  module: _omn9262_start\n"
            "  class: StartEvent\n"
            "handler_routing:\n"
            "  routing_strategy: payload_type_match\n"
            "  handlers:\n"
            "    - event_model:\n"
            "        name: StartEvent\n"
            "        module: _omn9262_start\n"
            "      handler:\n"
            "        name: HandlerA\n"
            "        module: _omn9262_ha\n"
            "      output_events:\n"
            "        - MidEvent\n"
            "    - event_model:\n"
            "        name: MidEvent\n"
            "        module: _omn9262_mid\n"
            "      handler:\n"
            "        name: HandlerB\n"
            "        module: _omn9262_hb\n"
            "      output_events:\n"
            "        - DoneEvent\n"
            "    - event_model:\n"
            "        name: DoneEvent\n"
            "        module: _omn9262_done\n"
            "      handler:\n"
            "        name: HandlerCTerminal\n"
            "        module: _omn9262_hc\n"
            "      subscribe_topic: evt.tr.done.v1\n"
            "      output_events: []\n"
        )
        workflow = tmp_path / "contract.yaml"
        workflow.write_text(contract_yaml)

        runtime = RuntimeLocal(
            workflow_path=workflow,
            state_root=tmp_path / "state",
            timeout=10,
        )
        result = await runtime.run_async()

        assert result == EnumWorkflowResult.COMPLETED
        assert len(terminal_invocations) == 1, (
            "Terminal reducer HandlerCTerminal was not invoked"
        )

        state_file = tmp_path / "state" / "workflow_result.json"
        assert state_file.exists(), "workflow_result.json was not written to disk"
        data = json.loads(state_file.read_text())
        assert data["result"] == "completed"
        assert data["exit_code"] == 0

    finally:
        for mod_name in mod_map:
            sys.modules.pop(mod_name, None)
