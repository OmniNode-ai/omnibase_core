# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-22362: ``onex run-node`` resolves its broker from the node's contract overlay.

Operator ruling 2026-11-03: "The default broker should be in the contract overlay."
These are the falsifiers. They drive the real command and the real resolver
discovery (the ``onex.node_broker_resolvers`` entry-point group) against a
resolver that reads real overlay files, so each case would fail on the merge base,
where the broker was ``$KAFKA_BOOTSTRAP_SERVERS``:

* a Redpanda overlay (``type: kafka`` with a lane) selects that lane's broker with
  the environment variable set to a different, wrong value;
* an in-memory overlay hosts the node in this process and dials no broker;
* a node with no overlay is refused with a typed error naming the overlay path.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Iterator
from importlib.metadata import EntryPoint
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_event_bus_type import EnumEventBusType
from omnibase_core.models.event_bus.model_node_broker_binding import (
    ModelNodeBrokerBinding,
)
from omnibase_core.models.event_bus.model_node_broker_resolution_error import (
    ModelNodeBrokerResolutionError,
)
from omnibase_core.protocols.runtime.protocol_node_broker_resolver import (
    ProtocolNodeBrokerResolver,
)

pytestmark = pytest.mark.unit

_MODULE = "tests.unit.cli.test_cli_run_node_broker_overlay"
_COMMAND_TOPIC = "onex.cmd.omn22362.broker-overlay.v1"
_TERMINAL_TOPIC = "onex.evt.omn22362.broker-overlay-completed.v1"
_ENTRY_POINTS_TARGET = (
    "omnibase_core.models.event_bus.model_node_broker_binding.entry_points"
)
_NODE = "node_broker_overlay_probe"


class ModelOverlayProbeCommand(BaseModel):
    """The probe node's input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: uuid.UUID = Field(...)
    prompt: str = Field(default="")


class HandlerOverlayProbe:
    """Answers with the prompt it was given, so the test sees the node really ran here."""

    async def handle(self, payload: ModelOverlayProbeCommand) -> dict[str, str]:
        await asyncio.sleep(0)
        return {"status": "success", "echo": payload.prompt}


class OverlayFileResolver:
    """A resolver that reads ``<root>/<node>/overlay.yaml``, shaped like the infra one."""

    root: Path = Path("/unset")
    lane_brokers: dict[str, str] = {"dev": "redpanda-dev:19092"}

    def resolve_node_broker(self, node_id: str) -> ModelNodeBrokerBinding:
        overlay = self.root / node_id / "overlay.yaml"
        if not overlay.is_file():
            raise ModelNodeBrokerResolutionError(
                f"{node_id} declares no event_bus: overlay {overlay} does not exist",
                overlay_path=str(overlay),
            )
        declared = yaml.safe_load(overlay.read_text(encoding="utf-8"))["event_bus"]
        if declared["type"] == "inmemory":
            return ModelNodeBrokerBinding(
                bus_type=EnumEventBusType.INMEMORY, overlay_path=overlay
            )
        return ModelNodeBrokerBinding(
            bus_type=EnumEventBusType.KAFKA,
            overlay_path=overlay,
            lane=declared["lane"],
            bootstrap_servers=self.lane_brokers[declared["lane"]],
            security_protocol="PLAINTEXT",
        )


@pytest.fixture
def overlays(tmp_path: Path) -> Path:
    OverlayFileResolver.root = tmp_path / "overlays"
    return OverlayFileResolver.root


@pytest.fixture
def registered_resolver(overlays: Path) -> Iterator[None]:
    ep = EntryPoint(
        name="overlay-file",
        value=f"{_MODULE}:OverlayFileResolver",
        group="onex.node_broker_resolvers",
    )
    with patch(_ENTRY_POINTS_TARGET, return_value=[ep]):
        yield


def _declare(overlays: Path, event_bus: dict[str, str]) -> Path:
    path = overlays / _NODE / "overlay.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"event_bus": event_bus}), encoding="utf-8")
    return path


def _write_contract(target: Path) -> Path:
    contract = {
        "workflow_id": "omn-22362-broker-overlay",
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
                    "handler": {"module": _MODULE, "name": "HandlerOverlayProbe"},
                    "event_model": {
                        "module": _MODULE,
                        "name": "ModelOverlayProbeCommand",
                    },
                    "output_topic": _TERMINAL_TOPIC,
                }
            ],
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")
    return target


def test_resolver_double_satisfies_the_protocol() -> None:
    assert isinstance(OverlayFileResolver(), ProtocolNodeBrokerResolver)


def test_redpanda_overlay_selects_the_lane_broker_and_ignores_the_environment(
    registered_resolver: None,
    overlays: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from omnibase_core.cli.cli_run_node import run_node

    _declare(overlays, {"type": "kafka", "lane": "dev"})
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "ambient-wrong-broker:1")
    with (
        patch(
            "omnibase_core.cli.cli_run_node._resolve_node_topics",
            return_value=(Path("/tmp/c.yaml"), _COMMAND_TOPIC, _TERMINAL_TOPIC, False),
        ),
        patch(
            "omnibase_core.cli.cli_run_node.publish_and_poll",
            return_value={"payload": {"status": "success"}},
        ) as dial,
    ):
        result = CliRunner().invoke(run_node, [_NODE, "--input", "{}"])

    assert result.exit_code == 0, result.output
    assert dial.call_args.kwargs["bootstrap_servers"] == "redpanda-dev:19092"
    assert dial.call_args.kwargs["client_security"] == {
        "security.protocol": "PLAINTEXT"
    }


def test_inmemory_overlay_hosts_the_node_in_process_and_dials_no_broker(
    registered_resolver: None, overlays: Path, tmp_path: Path
) -> None:
    from omnibase_core.cli.cli_run_node import run_node

    _declare(overlays, {"type": "inmemory"})
    contract = _write_contract(tmp_path / "contract.yaml")
    with (
        patch(
            "omnibase_core.cli.cli_run_node._resolve_node_topics",
            return_value=(contract, _COMMAND_TOPIC, _TERMINAL_TOPIC, False),
        ),
        patch("omnibase_core.cli.cli_run_node.publish_and_poll") as dial,
    ):
        result = CliRunner().invoke(
            run_node, [_NODE, "--input", json.dumps({"prompt": "hello"})]
        )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"status": "success", "echo": "hello"}
    dial.assert_not_called()


def test_missing_overlay_is_refused_naming_the_overlay_path(
    registered_resolver: None, overlays: Path
) -> None:
    from omnibase_core.cli.cli_run_node import run_node

    with patch("omnibase_core.cli.cli_run_node.publish_and_poll") as dial:
        result = CliRunner().invoke(run_node, [_NODE, "--input", "{}"])

    expected = str(overlays / _NODE / "overlay.yaml")
    assert result.exit_code == 1
    envelope = json.loads(result.output)
    assert envelope["error_type"] == "SkillRoutingError"
    assert envelope["cause"] == "ModelNodeBrokerResolutionError"
    assert envelope["overlay_path"] == expected
    assert expected in envelope["message"]
    dial.assert_not_called()


def test_missing_overlay_is_refused_even_with_the_old_environment_variable_set(
    registered_resolver: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from omnibase_core.cli.cli_run_node import run_node

    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "ambient-wrong-broker:1")
    with patch("omnibase_core.cli.cli_run_node.publish_and_poll") as dial:
        result = CliRunner().invoke(run_node, [_NODE, "--input", "{}"])

    assert result.exit_code == 1
    assert "overlay" in json.loads(result.output)["message"]
    dial.assert_not_called()


def test_two_registered_resolvers_are_refused() -> None:
    eps = [
        EntryPoint("a", f"{_MODULE}:OverlayFileResolver", "onex.node_broker_resolvers"),
        EntryPoint("b", f"{_MODULE}:OverlayFileResolver", "onex.node_broker_resolvers"),
    ]
    with patch(_ENTRY_POINTS_TARGET, return_value=eps):
        with pytest.raises(ModelNodeBrokerResolutionError, match="more than one"):
            ModelNodeBrokerBinding.for_node(_NODE)


def test_provider_that_is_not_a_resolver_is_refused() -> None:
    ep = EntryPoint(
        "bad", f"{_MODULE}:HandlerOverlayProbe", "onex.node_broker_resolvers"
    )
    with patch(_ENTRY_POINTS_TARGET, return_value=[ep]):
        with pytest.raises(ModelNodeBrokerResolutionError):
            ModelNodeBrokerBinding.for_node(_NODE)


def test_binding_validation_ties_the_transport_to_the_bus_type() -> None:
    overlay = Path("/o/overlay.yaml")
    with pytest.raises(ValueError, match="needs bootstrap_servers"):
        ModelNodeBrokerBinding(bus_type=EnumEventBusType.KAFKA, overlay_path=overlay)
    with pytest.raises(ValueError, match="no broker"):
        ModelNodeBrokerBinding(
            bus_type=EnumEventBusType.INMEMORY,
            overlay_path=overlay,
            bootstrap_servers="x:1",
        )
