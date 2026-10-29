# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the contract walker check node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.contract_walker_check.model_contract_walker_check_input import (
    ModelContractWalkerCheckInput,
)
from omnibase_core.nodes.node_contract_walker_check_compute.handler import (
    NodeContractWalkerCheckCompute,
)
from omnibase_core.nodes.node_contract_walker_check_compute.runtime_contract_walker_check import (
    main,
)

pytestmark = pytest.mark.unit

_V = {"major": 1, "minor": 0, "patch": 0}


def _state(name: str, *, terminal: bool = False) -> dict[str, object]:
    state: dict[str, object] = {
        "version": _V,
        "state_name": name,
        "state_type": "terminal" if terminal else "operational",
        "description": name,
    }
    if terminal:
        state["is_terminal"] = True
        state["is_recoverable"] = False
    return state


def _write_machine(root: Path) -> None:
    machine = {
        "version": _V,
        "state_machine_name": "m",
        "state_machine_version": _V,
        "description": "m",
        "initial_state": "START",
        "terminal_states": ["DONE"],
        "error_states": [],
        "states": [_state("START"), _state("DONE", terminal=True)],
        "transitions": [
            {
                "version": _V,
                "transition_name": "start_go_done",
                "from_state": "START",
                "to_state": "DONE",
                "trigger": "go",
            }
        ],
    }
    directory = root / "node_walk_orchestrator"
    directory.mkdir(parents=True)
    (directory / "contract.yaml").write_text(
        yaml.safe_dump({"node_type": "ORCHESTRATOR_GENERIC", "state_machine": machine}),
        encoding="utf-8",
    )


def test_handle_walks_a_machine(tmp_path: Path) -> None:
    _write_machine(tmp_path)
    report = NodeContractWalkerCheckCompute().handle(
        ModelContractWalkerCheckInput(roots=(tmp_path,))
    )
    assert report.summary.walked_contracts == 1
    assert report.summary.golden_paths == 1


def test_handle_empty_tree_walks_nothing(tmp_path: Path) -> None:
    report = NodeContractWalkerCheckCompute().handle(
        ModelContractWalkerCheckInput(roots=(tmp_path,), max_product_states=5)
    )
    assert report.summary.walked_contracts == 0
    assert report.summary.workflows == 0


def test_main_is_report_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_machine(tmp_path / "tree")
    assert main([str(tmp_path / "tree")]) == 0
    printed = capsys.readouterr().out
    assert "report-only" in printed
    assert "node_walk_orchestrator" in printed
    assert main([str(tmp_path / "empty")]) == 0
    assert "walked 0" in capsys.readouterr().out
