# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-25564: ``onex run-node`` ends non-zero when the run's recorded events were not delivered.

A node hosted in process (overlay ``type: inmemory``) hands its recorded events to the installed
forwarder. When the forwarder could not reach the hosted bus, ``RuntimeLocal`` wrote a degraded
bus reading and one stderr line, and the command still exited 0 with nothing delivered. The
command now exits non-zero and carries the forwarder's reason (which names the missing value and
where it looked) in its error envelope.

Each failing case fails on the merge base, where that run exited 0.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Iterator, Sequence
from importlib.metadata import EntryPoint
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner, Result
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_event_bus_type import EnumEventBusType
from omnibase_core.models.event_bus.model_node_broker_binding import (
    ModelNodeBrokerBinding,
)

pytestmark = pytest.mark.unit

_MODULE = "tests.unit.cli.test_cli_run_node_undelivered"
_COMMAND_TOPIC = "onex.cmd.omn25564.undelivered.v1"
_TERMINAL_TOPIC = "onex.evt.omn25564.undelivered-completed.v1"
_NODE = "node_undelivered_probe"
_REFUSAL = (
    "runtime bus forwarder could not reach the hosted bus: no workspace root: looked at "
    "$OMNIBASE_PATH (unset or blank) and the host config directory (no *.env declares it)"
)


class ModelUndeliveredProbeCommand(BaseModel):
    """The probe node's input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")


class HandlerUndeliveredProbe:
    """Answers with the prompt it was given."""

    async def handle(self, payload: ModelUndeliveredProbeCommand) -> dict[str, str]:
        await asyncio.sleep(0)
        return {"status": "success", "echo": payload.prompt}


class InmemoryResolver:
    """Declares the probe node as hosted in process."""

    def resolve_node_broker(self, node_id: str) -> ModelNodeBrokerBinding:
        return ModelNodeBrokerBinding(
            bus_type=EnumEventBusType.INMEMORY, overlay_path=Path("overlay.yaml")
        )


class RefusingForwarder:
    """A forwarder that cannot reach the hosted bus."""

    def forward(self, events: Sequence[object]) -> dict[str, object]:
        raise RuntimeError(_REFUSAL)


class PartialForwarder:
    """A forwarder that carries the events and refuses the run's own command by name."""

    def forward(self, events: Sequence[object]) -> dict[str, object]:
        return {
            "forwarded": 1,
            "failed": 1,
            "detail": "1 event(s) refused: command topic",
        }


class DeliveringForwarder:
    """A forwarder that carries every event."""

    def forward(self, events: Sequence[object]) -> dict[str, object]:
        return {"forwarded": len(events), "failed": 0, "detail": None}


def _write_contract(target: Path) -> Path:
    contract = {
        "workflow_id": "omn-25564-undelivered",
        "name": _NODE,
        "terminal_event": _TERMINAL_TOPIC,
        "event_bus": {
            "subscribe_topics": [_COMMAND_TOPIC],
            "publish_topics": [_TERMINAL_TOPIC],
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "operation": "start",
                    "handler": {"module": _MODULE, "name": "HandlerUndeliveredProbe"},
                    "event_model": {
                        "module": _MODULE,
                        "name": "ModelUndeliveredProbeCommand",
                    },
                    "output_topic": _TERMINAL_TOPIC,
                }
            ],
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")
    return target


@pytest.fixture
def forwarder_name(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[str]:
    """Install the forwarder class the test names, with the probe node hosted in process."""
    name: str = request.param
    forwarder = EntryPoint(
        "probe-forwarder", f"{_MODULE}:{name}", "onex.runtime_bus_forwarders"
    )
    resolver = EntryPoint(
        "inmemory", f"{_MODULE}:InmemoryResolver", "onex.node_broker_resolvers"
    )
    with (
        patch(
            "omnibase_core.models.event_bus.model_runtime_bus_binding.entry_points",
            return_value=[forwarder],
        ),
        patch(
            "omnibase_core.models.event_bus.model_node_broker_binding.entry_points",
            return_value=[resolver],
        ),
        patch(
            "omnibase_core.cli.cli_run_node._resolve_node_topics",
            return_value=(
                _write_contract(tmp_path / "contract.yaml"),
                _COMMAND_TOPIC,
                _TERMINAL_TOPIC,
                False,
            ),
        ),
    ):
        yield name


def _run() -> Result:
    from omnibase_core.cli.cli_run_node import run_node

    return CliRunner().invoke(
        run_node, [_NODE, "--input", json.dumps({"prompt": "hi"})]
    )


@pytest.mark.parametrize("forwarder_name", ["RefusingForwarder"], indirect=True)
def test_ac2_undelivered_run_exits_non_zero_carrying_the_forwarders_reason(
    forwarder_name: str,
) -> None:
    result = _run()

    assert result.exit_code == 1, result.output
    envelope = json.loads(result.stdout)
    assert envelope["error_type"] == "SkillRoutingError"
    assert "not delivered" in envelope["message"]
    assert "inmemory_forwarded" in envelope["message"]
    assert _REFUSAL in envelope["message"]
    assert "DEGRADED BUS" in result.stderr


@pytest.mark.parametrize("forwarder_name", ["DeliveringForwarder"], indirect=True)
def test_delivered_run_still_answers_and_exits_zero(forwarder_name: str) -> None:
    result = _run()

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"status": "success", "echo": "hi"}


@pytest.mark.parametrize("forwarder_name", ["PartialForwarder"], indirect=True)
def test_partial_delivery_keeps_the_answer_and_says_so_on_stderr(
    forwarder_name: str,
) -> None:
    result = _run()

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"status": "success", "echo": "hi"}
    assert "1 not delivered" in result.stderr
