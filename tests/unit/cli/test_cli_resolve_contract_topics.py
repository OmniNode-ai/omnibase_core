# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for cli_resolve_contract_topics (OMN-10512).

Covers:
    - unknown node_id raises ModelOnexError listing known nodes
    - resolve_node_contract returns a valid Path ending in contract.yaml
    - resolve_contract_topics returns (command_topic, terminal_topic) from subscribe_topics
    - resolve_contract_topics returns command_topic from event_bus.command_topic (priority a)
    - missing subscribe_topics raises ModelOnexError
    - missing terminal_event raises ModelOnexError
    - terminal_event as dict with .topic field is resolved correctly
    - multiple subscribe_topics warns to stderr and uses first
"""

from __future__ import annotations

import warnings
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

from omnibase_core.cli.cli_resolve_contract_topics import (
    resolve_contract_topics,
    resolve_node_contract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_contract(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "contract.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _fake_ep(name: str, value: str) -> object:
    class _EP:
        pass

    ep = _EP()
    # NOTE(OMN-10512): dynamic attr assignment on a bare class for entry-point test stub.
    ep.name = name  # type: ignore[attr-defined]
    ep.value = value  # type: ignore[attr-defined]
    ep.dist = "local-fake"  # type: ignore[attr-defined]
    return ep


# ---------------------------------------------------------------------------
# resolve_node_contract
# ---------------------------------------------------------------------------


def test_unknown_node_id_raises_model_onex_error_with_known_list() -> None:
    with patch(
        "omnibase_core.cli.cli_resolve_contract_topics.entry_points",
        return_value=[_fake_ep("node_real", "some.module:Node")],
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_node_contract("node_does_not_exist")
    msg = str(exc_info.value)
    assert "node_does_not_exist" in msg
    assert "node_real" in msg


def test_resolve_node_contract_returns_contract_path(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "fake_node_pkg"
    pkg_dir.mkdir()
    contract = pkg_dir / "contract.yaml"
    contract.write_text("name: fake\n", encoding="utf-8")

    spec = ModuleSpec("fake_node_pkg", loader=None, is_package=True)
    spec.submodule_search_locations = [str(pkg_dir)]

    with (
        patch(
            "omnibase_core.cli.cli_resolve_contract_topics.entry_points",
            return_value=[_fake_ep("node_fake", "fake_node_pkg:Node")],
        ),
        patch(
            "omnibase_core.cli.cli_resolve_contract_topics.importlib.util.find_spec",
            return_value=spec,
        ),
    ):
        result = resolve_node_contract("node_fake")

    assert result.name == "contract.yaml"
    assert result.exists()


def test_missing_packaged_contract_raises_file_not_found(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "fake_node_pkg_nocontract"
    pkg_dir.mkdir()

    spec = ModuleSpec("fake_node_pkg_nocontract", loader=None, is_package=True)
    spec.submodule_search_locations = [str(pkg_dir)]

    with (
        patch(
            "omnibase_core.cli.cli_resolve_contract_topics.entry_points",
            return_value=[_fake_ep("node_nocontract", "fake_node_pkg_nocontract:Node")],
        ),
        patch(
            "omnibase_core.cli.cli_resolve_contract_topics.importlib.util.find_spec",
            return_value=spec,
        ),
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_node_contract("node_nocontract")
    assert "contract.yaml" in str(exc_info.value)


def test_duplicate_entry_point_raises_model_onex_error() -> None:
    ep1 = _fake_ep("node_dup", "pkg_a:Node")
    ep2 = _fake_ep("node_dup", "pkg_b:Node")

    with patch(
        "omnibase_core.cli.cli_resolve_contract_topics.entry_points",
        return_value=[ep1, ep2],
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_node_contract("node_dup")
    assert "Duplicate" in str(exc_info.value)


# ---------------------------------------------------------------------------
# resolve_contract_topics — happy paths
# ---------------------------------------------------------------------------


def test_resolve_contract_topics_from_subscribe_topics(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        "subscribe_topics:\n"
        "  - onex.cmd.omnimarket.duplication-sweep-start.v1\n"
        "terminal_event: onex.evt.omnimarket.duplication-sweep-completed.v1\n",
    )
    cmd, terminal = resolve_contract_topics(contract)
    assert cmd == "onex.cmd.omnimarket.duplication-sweep-start.v1"
    assert terminal == "onex.evt.omnimarket.duplication-sweep-completed.v1"


def test_resolve_contract_topics_event_bus_command_topic_takes_priority(
    tmp_path: Path,
) -> None:
    contract = _write_contract(
        tmp_path,
        "subscribe_topics:\n"
        "  - onex.cmd.omnimarket.ignored-topic.v1\n"
        "event_bus:\n"
        "  command_topic: onex.cmd.omnimarket.explicit-command.v1\n"
        "terminal_event: onex.evt.omnimarket.done.v1\n",
    )
    cmd, terminal = resolve_contract_topics(contract)
    assert cmd == "onex.cmd.omnimarket.explicit-command.v1"
    assert terminal == "onex.evt.omnimarket.done.v1"


def test_resolve_contract_topics_terminal_event_as_dict(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        "subscribe_topics:\n"
        "  - onex.cmd.svc.start.v1\n"
        "terminal_event:\n"
        "  topic: onex.evt.svc.completed.v1\n",
    )
    cmd, terminal = resolve_contract_topics(contract)
    assert cmd == "onex.cmd.svc.start.v1"
    assert terminal == "onex.evt.svc.completed.v1"


def test_resolve_contract_topics_multiple_subscribe_topics_warns(
    tmp_path: Path,
) -> None:
    contract = _write_contract(
        tmp_path,
        "subscribe_topics:\n"
        "  - onex.cmd.svc.first.v1\n"
        "  - onex.cmd.svc.second.v1\n"
        "terminal_event: onex.evt.svc.done.v1\n",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cmd, _ = resolve_contract_topics(contract)
    assert cmd == "onex.cmd.svc.first.v1"
    assert any("multiple subscribe_topics" in str(w.message) for w in caught)


# ---------------------------------------------------------------------------
# resolve_contract_topics — error paths
# ---------------------------------------------------------------------------


def test_missing_subscribe_topics_raises_model_onex_error(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        "name: no_subscribe\nterminal_event: onex.evt.svc.done.v1\n",
    )
    with pytest.raises(ModelOnexError) as exc_info:
        resolve_contract_topics(contract)
    assert "subscribe_topics" in str(exc_info.value)
    assert str(contract) in str(exc_info.value)


def test_missing_terminal_event_raises_model_onex_error(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        "subscribe_topics:\n  - onex.cmd.svc.start.v1\n",
    )
    with pytest.raises(ModelOnexError) as exc_info:
        resolve_contract_topics(contract)
    assert "terminal_event" in str(exc_info.value)
    assert str(contract) in str(exc_info.value)


def test_empty_subscribe_topics_list_raises_model_onex_error(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        "subscribe_topics: []\nterminal_event: onex.evt.svc.done.v1\n",
    )
    with pytest.raises(ModelOnexError) as exc_info:
        resolve_contract_topics(contract)
    assert "subscribe_topics" in str(exc_info.value)
